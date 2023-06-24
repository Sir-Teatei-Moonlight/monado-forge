import bpy
import io
import math
import mathutils
import os

from . classes import *
from . utils import *
from . modify_funcs import *

def realise_results(forgeResults, mainName, self, context):
	printProgress = context.scene.monado_forge_main.printProgress
	if not forgeResults:
		self.report({"ERROR"}, "Compiled results were empty. There might be more information in the console.")
		return {"CANCELLED"}
	if printProgress:
		print("Converting processed data into Blender objects.")
	boneSize = context.scene.monado_forge_import.boneSize
	positionEpsilon = context.scene.monado_forge_main.positionEpsilon
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
	createDummyShader = context.scene.monado_forge_import.createDummyShader
	armaturesCreated = 0
	# we create the external armature (if any) first so it gets name priority
	if context.scene.monado_forge_import.importToCursor:
		pos = context.scene.cursor.location
		rot = context.scene.cursor.rotation_euler
	else:
		pos = (0,0,0)
		rot = (0,0,0)
	externalSkeleton = forgeResults.getExternalSkeleton()
	if externalSkeleton:
		boneList = externalSkeleton.getBones()
		armatureName = mainName
		externalArmature = create_armature_from_bones(boneList,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
		armaturesCreated += 1
	else:
		externalArmature = None
	baseSkeleton = forgeResults.getSkeleton()
	if baseSkeleton:
		boneList = baseSkeleton.getBones()
		armatureName = mainName
		baseArmature = create_armature_from_bones(boneList,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
		armaturesCreated += 1
	else:
		baseArmature = None
	if printProgress:
		print("Finished creating "+str(armaturesCreated)+" armatures.")
	
	materials = forgeResults.getMaterials()
	newMatsByIndex = {}
	for m,mat in enumerate(materials):
		newMat = bpy.data.materials.new(name=mat.getName())
		if context.scene.monado_forge_import.fixedViewportColour:
			newMat.diffuse_color = context.scene.monado_forge_import.viewportColour
		else:
			newMat.diffuse_color = mat.getViewportColour()
		newMat.blend_method = "OPAQUE" # the most likely option
		newMat.shadow_method = "OPAQUE"
		newMat.use_backface_culling = True # more likely than not
		newMat.use_nodes = True # the default creation is "Principled BSDF" into "Material Output"
		n = newMat.node_tree.nodes
		n.remove(n.get("Principled BSDF"))
		shaderSubnode = n.new("ShaderNodeGroup")
		shaderSubnode.location = [700,300]
		if createDummyShader:
			try:
				dummyShader = bpy.data.node_groups["DummyShader"]
			except KeyError:
				dummyShader = bpy.data.node_groups.new("DummyShader","ShaderNodeTree")
				dummyShader.inputs.new("NodeSocketColor","Base Color")
				dummyShader.outputs.new("NodeSocketShader","BSDF")
				dummyN = dummyShader.nodes
				dummyInput = dummyN.new("NodeGroupInput")
				dummyInput.location = [-400,0]
				dummyOutput = dummyN.new("NodeGroupOutput")
				dummyOutput.location = [400,0]
				dummyBSDF = dummyN.new("ShaderNodeBsdfPrincipled")
				dummyBSDF.location = [0,300]
				dummyShader.links.new(dummyInput.outputs[0],dummyBSDF.inputs["Base Color"])
				dummyShader.links.new(dummyBSDF.outputs["BSDF"],dummyOutput.inputs[0])
			shaderSubnode.node_tree = dummyShader
			newMat.node_tree.links.new(shaderSubnode.outputs[0],n.get("Material Output").inputs[0])
		baseColourNode = n.new("ShaderNodeRGB")
		baseColourNode.outputs[0].default_value = mat.getBaseColour()
		baseColourNode.label = "Base Colour"
		baseColourNode.location = [-650,300]
		n.get("Material Output").location = [950,300]
		texNodes = []
		mirroring = {"":[],"x":[],"y":[],"xy":[]}
		if not mat.getTextures(): # no textures, plug in the base colour directly
			newMat.node_tree.links.new(baseColourNode.outputs[0],shaderSubnode.inputs["Base Color"])
		for ti,t in enumerate(mat.getTextures()):
			texNode = n.new("ShaderNodeTexImage")
			texNode.extension = "EXTEND"
			repeat = t.getRepeating()
			if repeat[0] or repeat[1]: # Blender only supports "all extend" or "all repeat", so will have to make a new node to support mixed cases (probably not common)
				texNode.extension = "REPEAT"
			if repeat[0] != repeat[1]:
				print_warning("Texture "+t.getName()+" wants to be clamped in one direction but repeat in another, which is not yet supported (setting to repeat in both)")
			texNode.interpolation = "Closest"
			if t.isFiltered():
				texNode.interpolation = "Linear"
			texNode.image = bpy.data.images[t.getName()]
			# use the name to make a guess for whether this is colour data or not
			if any([
				"_NRM" in t.getName(),"_NML" in t.getName(), # normal
				"_MTL" in t.getName(), # metal
				"_SHY" in t.getName(), # gloss
				"_ALP" in t.getName(), # alpha
				"_GLO" in t.getName(), # glow/emit
				"_MSK" in t.getName(), # mask
				"_VEL" in t.getName(), # velocity (fur/hair map)
				"_DPS" in t.getName(), # displacement?
				"temp" in t.getName(), # channelised
				]):
					texNode.image.colorspace_settings.name = "Non-Color"
			tx = ti%4
			ty = ti//4
			texNode.location = [tx*250-325,ty*-250+300]
			# guess: the first texture is the base colour
			if ti == 0 and createDummyShader:
				newMat.node_tree.links.new(texNode.outputs["Color"],shaderSubnode.inputs["Base Color"])
			mir = t.getMirroring()
			mX = "x" if mir[0] else ""
			mY = "y" if mir[1] else ""
			mirroring[mX+mY].append(texNode)
			# for temp files, add a colour splitter for convenience
			if "temp" in t.getName():
				sepNode = n.new("ShaderNodeSeparateColor")
				sepNode.location = texNode.location + mathutils.Vector([125,-25])
				sepNode.hide = True
				newMat.node_tree.links.new(texNode.outputs["Color"],sepNode.inputs[0])
		uvCount = mat.getUVLayerCount() # this will probably result in overestimation, but that's okay
		for uv in range(uvCount):
			uvInputNode = n.new("ShaderNodeUVMap")
			uvInputNode.label = "UV Map "+str(uv+1)
			if mirroring[""]:
				uvInputNode.location = [-650,-125*uv+100]
				if uv == 0:
					for mt in mirroring[""]:
						newMat.node_tree.links.new(uvInputNode.outputs["UV"],mt.inputs["Vector"])
			if mirroring["x"]:
				print_warning("X-only texture mirror not yet supported (how'd you even get here)")
			if mirroring["y"]:
				print_warning("Y-only texture mirror not yet supported (how'd you even get here)")
			if mirroring["xy"]:
				uvInputNode.location = [-650,-175*uv+100]
				try:
					mirrorNodeGroup = bpy.data.node_groups["TexMirrorXY"]
				except KeyError:
					mirrorNodeGroup = bpy.data.node_groups.new("TexMirrorXY","ShaderNodeTree")
					mirrorNodeGroup.inputs.new("NodeSocketVector","Vector")
					mirrorNodeGroup.outputs.new("NodeSocketVector","Vector")
					mirN = mirrorNodeGroup.nodes
					mirInput = mirN.new("NodeGroupInput")
					mirInput.location = [-400,0]
					mirOutput = mirN.new("NodeGroupOutput")
					mirOutput.location = [400,0]
					sepNode = mirN.new("ShaderNodeSeparateXYZ")
					sepNode.location = [-200,0]
					merNode = mirN.new("ShaderNodeCombineXYZ")
					merNode.location = [200,0]
					mirXNode = mirN.new("ShaderNodeMath")
					mirXNode.operation = "PINGPONG"
					mirXNode.inputs[1].default_value = 1.0 # yay magic numbers (they're all called "Value")
					mirXNode.location = [0,-100]
					mirYNode = mirN.new("ShaderNodeMath")
					mirYNode.operation = "PINGPONG"
					mirYNode.inputs[1].default_value = 1.0
					mirYNode.location = [0,100]
					mirrorNodeGroup.links.new(mirInput.outputs[0],sepNode.inputs[0])
					mirrorNodeGroup.links.new(sepNode.outputs["X"],mirXNode.inputs["Value"])
					mirrorNodeGroup.links.new(sepNode.outputs["Y"],mirYNode.inputs["Value"])
					mirrorNodeGroup.links.new(mirXNode.outputs[0],merNode.inputs["X"])
					mirrorNodeGroup.links.new(mirYNode.outputs[0],merNode.inputs["Y"])
					mirrorNodeGroup.links.new(sepNode.outputs["Z"],merNode.inputs["Z"])
					mirrorNodeGroup.links.new(merNode.outputs[0],mirOutput.inputs[0])
				mirrorNode = n.new("ShaderNodeGroup")
				mirrorNode.node_tree = mirrorNodeGroup
				mirrorNode.location = [-650,-175*uv-25]
				mirrorNode.hide = True
				for mt in mirroring["xy"]:
					newMat.node_tree.links.new(uvInputNode.outputs["UV"],mirrorNode.inputs[0])
					if uv == 0:
						newMat.node_tree.links.new(mirrorNode.outputs[0],mt.inputs["Vector"])
		for xi,x in enumerate(mat.getExtraData()):
			extraDataNode = n.new("ShaderNodeValue")
			extraDataNode.outputs["Value"].default_value = x
			extraDataNode.label = "Extra Data Value"
			extraDataNode.location = [-475,xi*-100+300]
		newMatsByIndex[mat.getIndex()] = newMat
	
	meshes = forgeResults.getMeshes()
	for m,mesh in enumerate(meshes):
		if printProgress:
			print_progress_bar(m,len(meshes),"Mesh creation")
		bpy.ops.object.add(type="MESH", enter_editmode=False, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
		newMeshObject = bpy.context.view_layer.objects.active
		newMeshObject.name = f"{mainName}_mesh{m:03d}"
		meshData = newMeshObject.data
		meshData.name = "Mesh"
		vertCount = len(mesh.getVertices())
		meshData.from_pydata(mesh.getVertexPositionsList(),[],mesh.getFaceVertexIndexesList())
		for f in meshData.polygons:
			f.use_smooth = True
		meshData.use_auto_smooth = True
		if mesh.hasUVs():
			for layer in mesh.getUVLayerList():
				meshUVs = mesh.getVertexUVsLayer(layer)
				newUVsLayer = meshData.uv_layers.new(name="UV"+str(layer+1))
				for l in meshData.loops:
					newUVsLayer.data[l.index].uv = meshUVs[l.vertex_index]
		if mesh.hasNormals():
			normalsList = mesh.getVertexNormalsList()
			meshData.normals_split_custom_set_from_vertices(normalsList)
		if mesh.hasColours():
			coloursList = mesh.getVertexColoursList()
			vertCols = meshData.color_attributes.new("VertexColours","BYTE_COLOR","POINT")
			for i in range(len(coloursList)):
				vertCols.data[i].color = coloursList[i]
		if mesh.hasWeightIndexes() and baseArmature: # try the indexes method first (faster) (and also needs a baseArmature or it makes no sense)
			weightIndexes = set(mesh.getVertexWeightIndexesList())
			vertexesInEachGroup = {}
			for i in range(len(baseArmature.data.bones)):
				newMeshObject.vertex_groups.new(name=baseArmature.data.bones[i].name)
				vertexesInEachGroup[i] = mesh.getVertexesInWeightGroup(i)
			vertexesInEachSet = {}
			for i in weightIndexes:
				vertexesInEachSet[i] = mesh.getVertexesWithWeightIndex(i)
			weightSets = mesh.getWeightSets()
			for weightIndex in weightIndexes:
				try:
					weightSetData = weightSets[weightIndex]
				except IndexError: # can happen if the weight table override is high - the warning has already been given above
					continue
				for j in range(len(weightSetData[0])):
					groupIndex = weightSetData[0][j]
					groupValue = weightSetData[1][j]
					if groupValue == 0: continue
					vertexGroup = newMeshObject.vertex_groups[groupIndex]
					vertexesToAdd = vertexesInEachSet[weightIndex]
					vertexIDsToAdd = [v.getID() for v in vertexesToAdd]
					newMeshObject.vertex_groups[groupIndex].add(vertexIDsToAdd,groupValue,"ADD")
		elif mesh.hasWeights(): # no indexes, but do have directly-applied weights
			pass # not needed at the present time
		if mesh.hasShapes():
			shapes = mesh.getShapes()
			if not meshData.shape_keys:
				newMeshObject.shape_key_add(name="basis",from_mix=False)
			meshData.shape_keys.use_relative = True
			for s in shapes:
				newShape = newMeshObject.shape_key_add(name=s.getName(),from_mix=False)
				for vertexIndex,vertex in s.getVertices().items():
					newShape.data[vertexIndex].co += mathutils.Vector(vertex.getPosition())
		if not context.scene.monado_forge_import.skipMaterialImport:
			meshData.materials.append(newMatsByIndex[mesh.getMaterialIndex()])
		
		# import complete, cleanup time
		#meshData.validate(verbose=True)
		meshData.validate()
		meshData.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix().to_4x4(),shape_keys=True) # transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
		cleanup_mesh(context,newMeshObject,context.scene.monado_forge_import.cleanupLooseVertices,context.scene.monado_forge_import.cleanupEmptyGroups,context.scene.monado_forge_import.cleanupEmptyShapes)
		# attach mesh to base armature
		armatureMod = newMeshObject.modifiers.new("Armature","ARMATURE")
		armatureMod.object = baseArmature
		newMeshObject.parent = baseArmature
		# end of per-mesh loop
	if printProgress:
		print_progress_bar(len(meshes),len(meshes),"Mesh creation")
	# and finally, if there is an external armature, merge the base one into it
	if externalArmature:
		bpy.ops.object.select_all(action="DESELECT")
		baseArmature.select_set(True)
		externalArmature.select_set(True)
		bpy.context.view_layer.objects.active = externalArmature
		merge_selected_to_active_armatures(self, context, force=True)
	if printProgress:
		print("Finished creating "+str(len(meshes))+" meshes.")
	return {"FINISHED"}

def register():
	pass

def unregister():
	pass

#[...]