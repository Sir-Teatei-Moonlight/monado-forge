import bpy
import io
import math
import mathutils
import os

from . classes import *
from . utils import *
from . modify_funcs import *

# yes there's a lot of copy-paste code in here but nodes are a mess no matter what
def import_library_node(nodeId, self, context):
	prereqs = {
				"TexInset":["TBNMatrix"],
				}
	try:
		for pr in prereqs[nodeId]:
			if pr not in bpy.data.node_groups:
				import_library_node(pr,self,context)
	except KeyError: # no prereqs
		pass
	if nodeId == "BasicMetallic":
		nodeGroup = bpy.data.node_groups.new("BasicMetallic","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketColor","Base Colour")
		nodeGroup.inputs.new("NodeSocketColor","Ambient Colour")
		nodeGroup.inputs.new("NodeSocketColor","Emit Colour")
		nodeGroup.inputs.new("NodeSocketColor","Normal Map")
		nodeGroup.inputs.new("NodeSocketFloat","Alpha")
		nodeGroup.inputs.new("NodeSocketFloat","AO")
		nodeGroup.inputs.new("NodeSocketFloat","Metallic")
		nodeGroup.inputs.new("NodeSocketFloat","Glossiness")
		nodeGroup.inputs.new("NodeSocketFloat","Emit")
		nodeGroup.outputs.new("NodeSocketShader","BSDF")
		nodeGroup.inputs["Base Colour"].default_value = (0.5,0.5,0.5,1.0)
		nodeGroup.inputs["Ambient Colour"].default_value = (0.0,0.0,0.0,1.0)
		nodeGroup.inputs["Emit Colour"].default_value = (0.0,0.0,0.0,1.0)
		nodeGroup.inputs["Normal Map"].default_value = (0.5,0.5,1.0,1.0)
		nodeGroup.inputs["Alpha"].default_value = 1.0
		nodeGroup.inputs["AO"].default_value = 1.0
		nodeGroup.inputs["Metallic"].default_value = 0.0
		nodeGroup.inputs["Glossiness"].default_value = 0.5
		nodeGroup.inputs["Emit"].default_value = 0.0
		metalN = nodeGroup.nodes
		metalInput = metalN.new("NodeGroupInput")
		metalInput.location = [-400,0]
		metalOutput = metalN.new("NodeGroupOutput")
		metalOutput.location = [500,0]
		shaderNode = metalN.new("ShaderNodeBsdfPrincipled")
		shaderNode.location = [0,250]
		baseMixNode = metalN.new("ShaderNodeMixRGB")
		baseMixNode.blend_type = "MIX"
		baseMixNode.location = [-200,200]
		baseMixNode.inputs["Color1"].default_value = [0.0,0.0,0.0,1.0]
		ambientNode = metalN.new("ShaderNodeEmission")
		ambientNode.location = [-200,0]
		normalMapNode = metalN.new("ShaderNodeNormalMap")
		normalMapNode.location = [-200,-125]
		normalMapNode.hide = True
		roughToGlossNode = metalN.new("ShaderNodeMath")
		roughToGlossNode.operation = "SUBTRACT"
		roughToGlossNode.inputs[0].default_value = 1.0
		roughToGlossNode.location = [-200,-175]
		shaderAddNode = metalN.new("ShaderNodeAddShader")
		shaderAddNode.location = [300,0]
		nodeGroup.links.new(metalInput.outputs["Base Colour"],baseMixNode.inputs["Color2"])
		nodeGroup.links.new(metalInput.outputs["AO"],baseMixNode.inputs["Fac"])
		nodeGroup.links.new(metalInput.outputs["Ambient Colour"],ambientNode.inputs["Color"])
		nodeGroup.links.new(metalInput.outputs["Normal Map"],normalMapNode.inputs["Color"])
		nodeGroup.links.new(metalInput.outputs["Glossiness"],roughToGlossNode.inputs[1])
		nodeGroup.links.new(metalInput.outputs["Emit Colour"],shaderNode.inputs["Emission"])
		nodeGroup.links.new(metalInput.outputs["Alpha"],shaderNode.inputs["Alpha"])
		nodeGroup.links.new(metalInput.outputs["Metallic"],shaderNode.inputs["Metallic"])
		nodeGroup.links.new(metalInput.outputs["Emit"],shaderNode.inputs["Emission Strength"])
		nodeGroup.links.new(baseMixNode.outputs[0],shaderNode.inputs["Base Color"])
		nodeGroup.links.new(ambientNode.outputs[0],shaderAddNode.inputs[1])
		nodeGroup.links.new(normalMapNode.outputs[0],shaderNode.inputs["Normal"])
		nodeGroup.links.new(roughToGlossNode.outputs[0],shaderNode.inputs["Roughness"])
		nodeGroup.links.new(shaderNode.outputs["BSDF"],shaderAddNode.inputs[0])
		nodeGroup.links.new(shaderAddNode.outputs[0],metalOutput.inputs["BSDF"])
	elif nodeId == "BasicSpecular":
		if context.scene.render.engine != "BLENDER_EEVEE":
			self.report({"ERROR"}, "Only Eevee supports the specular workflow (as of this plugin version).\nThe node will be added anyway, but it might not work right.")
		nodeGroup = bpy.data.node_groups.new("BasicSpecular","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketColor","Base Colour")
		nodeGroup.inputs.new("NodeSocketColor","Specular Colour")
		nodeGroup.inputs.new("NodeSocketColor","Ambient Colour")
		nodeGroup.inputs.new("NodeSocketColor","Emit Colour")
		nodeGroup.inputs.new("NodeSocketColor","Normal Map")
		nodeGroup.inputs.new("NodeSocketFloat","Alpha")
		nodeGroup.inputs.new("NodeSocketFloat","AO")
		nodeGroup.inputs.new("NodeSocketFloat","Glossiness")
		nodeGroup.inputs.new("NodeSocketFloat","Emit")
		nodeGroup.outputs.new("NodeSocketShader","BSDF")
		nodeGroup.inputs["Base Colour"].default_value = (0.5,0.5,0.5,1.0)
		nodeGroup.inputs["Specular Colour"].default_value = (1.0,1.0,1.0,1.0)
		nodeGroup.inputs["Emit Colour"].default_value = (0.0,0.0,0.0,1.0)
		nodeGroup.inputs["Normal Map"].default_value = (0.5,0.5,1.0,1.0)
		nodeGroup.inputs["Alpha"].default_value = 1.0
		nodeGroup.inputs["AO"].default_value = 1.0
		nodeGroup.inputs["Glossiness"].default_value = 0.5
		nodeGroup.inputs["Emit"].default_value = 0.0
		specN = nodeGroup.nodes
		specInput = specN.new("NodeGroupInput")
		specInput.location = [-500,0]
		specOutput = specN.new("NodeGroupOutput")
		specOutput.location = [500,0]
		shaderNode = specN.new("ShaderNodeEeveeSpecular")
		shaderNode.location = [100,50]
		baseMixNode = specN.new("ShaderNodeMixRGB")
		baseMixNode.blend_type = "MIX"
		baseMixNode.location = [-300,200]
		baseMixNode.inputs["Color1"].default_value = [0.0,0.0,0.0,1.0]
		ambientNode = specN.new("ShaderNodeEmission")
		ambientNode.location = [-300,0]
		normalMapNode = specN.new("ShaderNodeNormalMap")
		normalMapNode.location = [-300,-125]
		normalMapNode.hide = True
		roughToGlossNode = specN.new("ShaderNodeMath")
		roughToGlossNode.operation = "SUBTRACT"
		roughToGlossNode.inputs[0].default_value = 1.0
		roughToGlossNode.location = [-300,-175]
		alphaInvertNode = specN.new("ShaderNodeMath")
		alphaInvertNode.operation = "SUBTRACT"
		alphaInvertNode.inputs[0].default_value = 1.0
		alphaInvertNode.location = [-100,50]
		emitMixNode = specN.new("ShaderNodeMixRGB")
		emitMixNode.blend_type = "MIX"
		emitMixNode.location = [-100,-150]
		emitMixNode.inputs["Color1"].default_value = [0.0,0.0,0.0,1.0]
		shaderAddNode = specN.new("ShaderNodeAddShader")
		shaderAddNode.location = [300,0]
		nodeGroup.links.new(specInput.outputs["Base Colour"],baseMixNode.inputs["Color2"])
		nodeGroup.links.new(specInput.outputs["AO"],baseMixNode.inputs["Fac"])
		nodeGroup.links.new(specInput.outputs["Ambient Colour"],ambientNode.inputs["Color"])
		nodeGroup.links.new(specInput.outputs["Normal Map"],normalMapNode.inputs["Color"])
		nodeGroup.links.new(specInput.outputs["Glossiness"],roughToGlossNode.inputs[1])
		nodeGroup.links.new(specInput.outputs["Alpha"],alphaInvertNode.inputs[1])
		nodeGroup.links.new(specInput.outputs["Specular Colour"],shaderNode.inputs["Specular"])
		nodeGroup.links.new(specInput.outputs["Emit Colour"],emitMixNode.inputs["Color2"])
		nodeGroup.links.new(specInput.outputs["Emit"],emitMixNode.inputs["Fac"])
		nodeGroup.links.new(baseMixNode.outputs[0],shaderNode.inputs["Base Color"])
		nodeGroup.links.new(ambientNode.outputs[0],shaderAddNode.inputs[1])
		nodeGroup.links.new(normalMapNode.outputs[0],shaderNode.inputs["Normal"])
		nodeGroup.links.new(alphaInvertNode.outputs[0],shaderNode.inputs["Transparency"])
		nodeGroup.links.new(roughToGlossNode.outputs[0],shaderNode.inputs["Roughness"])
		nodeGroup.links.new(emitMixNode.outputs[0],shaderNode.inputs["Emissive Color"])
		nodeGroup.links.new(shaderNode.outputs["BSDF"],shaderAddNode.inputs[0])
		nodeGroup.links.new(shaderAddNode.outputs[0],specOutput.inputs["BSDF"])
	elif nodeId == "TBNMatrix":
		# https://blender.stackexchange.com/questions/291989/how-would-i-get-the-full-tbn-matrix-from-just-a-normal-map
		nodeGroup = bpy.data.node_groups.new("TBNMatrix","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketColor","Normal Map")
		nodeGroup.inputs.new("NodeSocketVector","Tangent")
		nodeGroup.outputs.new("NodeSocketVector","Tangent")
		nodeGroup.outputs.new("NodeSocketVector","Bitangent")
		nodeGroup.outputs.new("NodeSocketVector","Normal")
		nodeGroup.inputs["Normal Map"].default_value = (0.5,0.5,1.0,1.0)
		tbnN = nodeGroup.nodes
		tbnInput = tbnN.new("NodeGroupInput")
		tbnInput.location = [-500,0]
		tbnOutput = tbnN.new("NodeGroupOutput")
		tbnOutput.location = [500,0]
		normalMapNode = tbnN.new("ShaderNodeNormalMap")
		normalMapNode.location = [-300,0]
		crossNode1 = tbnN.new("ShaderNodeVectorMath")
		crossNode1.operation = "CROSS_PRODUCT"
		crossNode1.location = [-100,0]
		crossNode2 = tbnN.new("ShaderNodeVectorMath")
		crossNode2.operation = "CROSS_PRODUCT"
		crossNode2.location = [100,0]
		normalizeNode1 = tbnN.new("ShaderNodeVectorMath")
		normalizeNode1.operation = "NORMALIZE"
		normalizeNode1.location = [300,0]
		normalizeNode1.hide = True
		normalizeNode2 = tbnN.new("ShaderNodeVectorMath")
		normalizeNode2.operation = "NORMALIZE"
		normalizeNode2.location = [300,-50]
		normalizeNode2.hide = True
		normalizeNode3 = tbnN.new("ShaderNodeVectorMath")
		normalizeNode3.operation = "NORMALIZE"
		normalizeNode3.location = [300,-100]
		normalizeNode3.hide = True
		nodeGroup.links.new(tbnInput.outputs["Normal Map"],normalMapNode.inputs["Color"])
		nodeGroup.links.new(tbnInput.outputs["Tangent"],crossNode1.inputs[1])
		nodeGroup.links.new(normalMapNode.outputs[0],crossNode1.inputs[0])
		nodeGroup.links.new(normalMapNode.outputs[0],crossNode2.inputs[1])
		nodeGroup.links.new(normalMapNode.outputs[0],normalizeNode3.inputs[0])
		nodeGroup.links.new(crossNode1.outputs[0],crossNode2.inputs[0])
		nodeGroup.links.new(crossNode1.outputs[0],normalizeNode2.inputs[0])
		nodeGroup.links.new(crossNode2.outputs[0],normalizeNode1.inputs[0])
		nodeGroup.links.new(normalizeNode1.outputs[0],tbnOutput.inputs["Tangent"])
		nodeGroup.links.new(normalizeNode2.outputs[0],tbnOutput.inputs["Bitangent"])
		nodeGroup.links.new(normalizeNode3.outputs[0],tbnOutput.inputs["Normal"])
	elif nodeId == "TexInset":
		# https://80.lv/articles/a-simple-way-to-make-a-parallax-effect-in-blender/
		# https://blender.stackexchange.com/questions/243048/fix-parallax-occlusion-mapping-from-the-side
		nodeGroup = bpy.data.node_groups.new("TexInset","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketVector","UV")
		nodeGroup.inputs.new("NodeSocketVector","Tangent")
		nodeGroup.inputs.new("NodeSocketColor","Normal Map")
		nodeGroup.inputs.new("NodeSocketFloat","Depth")
		nodeGroup.outputs.new("NodeSocketVector","UV")
		nodeGroup.inputs["Normal Map"].default_value = (0.5,0.5,1.0,1.0)
		insetN = nodeGroup.nodes
		insetInput = insetN.new("NodeGroupInput")
		insetInput.location = [-500,100]
		insetOutput = insetN.new("NodeGroupOutput")
		insetOutput.location = [500,0]
		geometryInput = insetN.new("ShaderNodeNewGeometry") # New! Geometry Advance 64 & Knuckles
		geometryInput.location = [-500,-100]
		normalizeNode = insetN.new("ShaderNodeVectorMath")
		normalizeNode.operation = "NORMALIZE"
		normalizeNode.location = [-300,-200]
		normalizeNode.hide = True
		depthTripleNode = insetN.new("ShaderNodeCombineXYZ")
		depthTripleNode.location = [-300,50]
		depthTripleNode.hide = True
		tbnNode = insetN.new("ShaderNodeGroup")
		tbnNode.node_tree = bpy.data.node_groups["TBNMatrix"]
		tbnNode.location = [-300,0]
		dotTangentNode = insetN.new("ShaderNodeVectorMath")
		dotTangentNode.operation = "DOT_PRODUCT"
		dotTangentNode.location = [-100,0]
		dotTangentNode.hide = True
		dotBitangentNode = insetN.new("ShaderNodeVectorMath")
		dotBitangentNode.operation = "DOT_PRODUCT"
		dotBitangentNode.location = [-100,-50]
		dotBitangentNode.hide = True
		dotNormalNode = insetN.new("ShaderNodeVectorMath")
		dotNormalNode.operation = "DOT_PRODUCT"
		dotNormalNode.location = [-100,-100]
		dotNormalNode.hide = True
		dotMergeNode = insetN.new("ShaderNodeCombineXYZ")
		dotMergeNode.location = [100,100]
		dotMergeNode.hide = True
		dotTransformNode = insetN.new("ShaderNodeVectorTransform")
		dotTransformNode.vector_type = "VECTOR"
		dotTransformNode.convert_from = "WORLD"
		dotTransformNode.convert_to = "OBJECT"
		dotTransformNode.location = [100,50]
		zSplitNode = insetN.new("ShaderNodeSeparateXYZ")
		zSplitNode.location = [100,-150]
		zSplitNode.hide = True
		divideNode = insetN.new("ShaderNodeVectorMath")
		divideNode.operation = "DIVIDE"
		divideNode.location = [100,-200]
		divideNode.hide = True
		multiplyNode = insetN.new("ShaderNodeVectorMath")
		multiplyNode.operation = "MULTIPLY"
		multiplyNode.location = [100,-250]
		multiplyNode.hide = True
		mappingNode = insetN.new("ShaderNodeMapping")
		mappingNode.vector_type = "TEXTURE"
		mappingNode.location = [300,50]
		nodeGroup.links.new(geometryInput.outputs["Incoming"],normalizeNode.inputs[0])
		nodeGroup.links.new(insetInput.outputs["Depth"],depthTripleNode.inputs[0])
		nodeGroup.links.new(insetInput.outputs["Depth"],depthTripleNode.inputs[1])
		nodeGroup.links.new(insetInput.outputs["Depth"],depthTripleNode.inputs[2])
		nodeGroup.links.new(insetInput.outputs["Tangent"],tbnNode.inputs["Tangent"])
		nodeGroup.links.new(insetInput.outputs["Normal Map"],tbnNode.inputs["Normal Map"])
		nodeGroup.links.new(tbnNode.outputs["Tangent"],dotTangentNode.inputs[0])
		nodeGroup.links.new(tbnNode.outputs["Bitangent"],dotBitangentNode.inputs[0])
		nodeGroup.links.new(tbnNode.outputs["Normal"],dotNormalNode.inputs[0])
		nodeGroup.links.new(normalizeNode.outputs[0],dotTangentNode.inputs[1])
		nodeGroup.links.new(normalizeNode.outputs[0],dotBitangentNode.inputs[1])
		nodeGroup.links.new(normalizeNode.outputs[0],dotNormalNode.inputs[1])
		nodeGroup.links.new(dotTangentNode.outputs["Value"],dotMergeNode.inputs[0])
		nodeGroup.links.new(dotBitangentNode.outputs["Value"],dotMergeNode.inputs[1])
		nodeGroup.links.new(dotNormalNode.outputs["Value"],dotMergeNode.inputs[2])
		nodeGroup.links.new(dotMergeNode.outputs[0],dotTransformNode.inputs[0])
		nodeGroup.links.new(dotTransformNode.outputs[0],zSplitNode.inputs[0])
		nodeGroup.links.new(dotTransformNode.outputs[0],divideNode.inputs[0])
		nodeGroup.links.new(zSplitNode.outputs["Z"],divideNode.inputs[1])
		nodeGroup.links.new(divideNode.outputs[0],multiplyNode.inputs[1])
		nodeGroup.links.new(depthTripleNode.outputs[0],multiplyNode.inputs[0])
		nodeGroup.links.new(multiplyNode.outputs[0],mappingNode.inputs["Location"])
		nodeGroup.links.new(insetInput.outputs["UV"],mappingNode.inputs["Vector"])
		nodeGroup.links.new(mappingNode.outputs[0],insetOutput.inputs["UV"])
	elif nodeId == "TexMirrorX":
		nodeGroup = bpy.data.node_groups.new("TexMirrorX","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketVector","Vector")
		nodeGroup.outputs.new("NodeSocketVector","Vector")
		mirN = nodeGroup.nodes
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
		mirXNode.location = [0,0]
		nodeGroup.links.new(mirInput.outputs[0],sepNode.inputs[0])
		nodeGroup.links.new(sepNode.outputs["X"],mirXNode.inputs["Value"])
		nodeGroup.links.new(mirXNode.outputs[0],merNode.inputs["X"])
		nodeGroup.links.new(sepNode.outputs["Y"],merNode.inputs["Y"])
		nodeGroup.links.new(sepNode.outputs["Z"],merNode.inputs["Z"])
		nodeGroup.links.new(merNode.outputs[0],mirOutput.inputs[0])
	elif nodeId == "TexMirrorY":
		nodeGroup = bpy.data.node_groups.new("TexMirrorY","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketVector","Vector")
		nodeGroup.outputs.new("NodeSocketVector","Vector")
		mirN = nodeGroup.nodes
		mirInput = mirN.new("NodeGroupInput")
		mirInput.location = [-400,0]
		mirOutput = mirN.new("NodeGroupOutput")
		mirOutput.location = [400,0]
		sepNode = mirN.new("ShaderNodeSeparateXYZ")
		sepNode.location = [-200,0]
		merNode = mirN.new("ShaderNodeCombineXYZ")
		merNode.location = [200,0]
		mirYNode = mirN.new("ShaderNodeMath")
		mirYNode.operation = "PINGPONG"
		mirYNode.inputs[1].default_value = 1.0
		mirYNode.location = [0,0]
		nodeGroup.links.new(mirInput.outputs[0],sepNode.inputs[0])
		nodeGroup.links.new(sepNode.outputs["Y"],mirYNode.inputs["Value"])
		nodeGroup.links.new(sepNode.outputs["X"],merNode.inputs["X"])
		nodeGroup.links.new(mirYNode.outputs[0],merNode.inputs["Y"])
		nodeGroup.links.new(sepNode.outputs["Z"],merNode.inputs["Z"])
		nodeGroup.links.new(merNode.outputs[0],mirOutput.inputs[0])
	elif nodeId == "TexMirrorXY":
		nodeGroup = bpy.data.node_groups.new("TexMirrorXY","ShaderNodeTree")
		nodeGroup.inputs.new("NodeSocketVector","Vector")
		nodeGroup.outputs.new("NodeSocketVector","Vector")
		mirN = nodeGroup.nodes
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
		mirXNode.location = [0,100]
		mirYNode = mirN.new("ShaderNodeMath")
		mirYNode.operation = "PINGPONG"
		mirYNode.inputs[1].default_value = 1.0
		mirYNode.location = [0,-100]
		nodeGroup.links.new(mirInput.outputs[0],sepNode.inputs[0])
		nodeGroup.links.new(sepNode.outputs["X"],mirXNode.inputs["Value"])
		nodeGroup.links.new(sepNode.outputs["Y"],mirYNode.inputs["Value"])
		nodeGroup.links.new(mirXNode.outputs[0],merNode.inputs["X"])
		nodeGroup.links.new(mirYNode.outputs[0],merNode.inputs["Y"])
		nodeGroup.links.new(sepNode.outputs["Z"],merNode.inputs["Z"])
		nodeGroup.links.new(merNode.outputs[0],mirOutput.inputs[0])
	else:
		self.report({"ERROR"}, "Node with id "+nodeId+" is not in the Forge library.")
		return {"CANCELLED"}
	self.report({"INFO"}, "Node group created: "+nodeGroup.name)

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
		armatureName = mainName
		externalArmature = create_armature_from_bones(externalSkeleton,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
		armaturesCreated += 1
	else:
		externalArmature = None
	baseSkeleton = forgeResults.getSkeleton()
	if baseSkeleton:
		armatureName = mainName
		baseArmature = create_armature_from_bones(baseSkeleton,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
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
		transparencyEnum = ["OPAQUE","CLIP","BLEND"]
		newMat.blend_method = transparencyEnum[mat.getTransparency()]
		shadowTransparencyEnum = ["OPAQUE","CLIP","OPAQUE"] # only binary shadows allowed
		newMat.shadow_method = shadowTransparencyEnum[mat.getTransparency()]
		newMat.use_backface_culling = mat.getCullingBack() # dunno what to do about any that cull front, so leaving it out
		newMat.show_transparent_back = True # not ideal but believed to be correct
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
		if createDummyShader and not mat.getTextures(): # no textures, plug in the base colour directly
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
			# use the name to guess what should be non-colour data
			if any([
				"_NRM" in t.getName(),"_NML" in t.getName(), # normal
				"_MTL" in t.getName(), # metal
				"_SHY" in t.getName(), # gloss
				"_ALP" in t.getName(), # alpha
				"_AO" in t.getName(), # ambient occlusion
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
		colourCount = mat.getColourLayerCount() # this will probably result in overestimation, but that's okay
		uvCount = mat.getUVLayerCount() # same
		pushdownValue = 100 # to keep track of node posititon across multiple for loops
		# we do UVs first because the node is shorter and they're more common than colours
		for uv in range(uvCount):
			uvInputNode = n.new("ShaderNodeUVMap")
			uvInputNode.label = "UV Map "+str(uv+1)
			uvInputNode.hide = True
			uvInputNode.location = [-650,pushdownValue]
			uvInputNode.uv_map = "UV"+str(uv+1)
			pushdownValue -= 40
			if mirroring[""] or not mat.getTextures(): # no textures means no mirroring defined: assume none
				if uv == 0:
					for mt in mirroring[""]:
						newMat.node_tree.links.new(uvInputNode.outputs["UV"],mt.inputs["Vector"])
			for mType in ["x","y","xy"]:
				if mirroring[mType]:
					try:
						mirrorNodeGroup = bpy.data.node_groups["TexMirror"+mType.upper()]
					except KeyError:
						import_library_node("TexMirror"+mType.upper(), self, context)
						mirrorNodeGroup = bpy.data.node_groups["TexMirror"+mType.upper()]
					mirrorNode = n.new("ShaderNodeGroup")
					mirrorNode.node_tree = mirrorNodeGroup
					mirrorNode.location = [-650,pushdownValue]
					pushdownValue -= 40
					mirrorNode.hide = True
					for mt in mirroring[mType]:
						newMat.node_tree.links.new(uvInputNode.outputs["UV"],mirrorNode.inputs[0])
						if uv == 0:
							newMat.node_tree.links.new(mirrorNode.outputs[0],mt.inputs["Vector"])
		for colour in range(colourCount):
			colourInputNode = n.new("ShaderNodeAttribute")
			colourInputNode.label = "Vertex Colours "+str(colour+1)
			colourInputNode.location = [-650,pushdownValue]
			colourInputNode.attribute_type = "GEOMETRY"
			colourInputNode.attribute_name = "VertexColours"+str(colour+1)
			colourInputNode.hide = True
			pushdownValue -= 40
		for xi,x in enumerate(mat.getExtraData()):
			extraDataNode = n.new("ShaderNodeValue")
			extraDataNode.outputs["Value"].default_value = x
			extraDataNode.label = "Extra Data Value "+str(xi+1)
			extraDataNode.location = [-475,xi*-100+300]
		newMatsByIndex[mat.getIndex()] = newMat
	
	meshes = forgeResults.getMeshes()
	for m,mesh in enumerate(meshes):
		if printProgress:
			print_progress_bar(m,len(meshes),"Mesh creation")
		bpy.ops.object.add(type="MESH", enter_editmode=False, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
		newMeshObject = bpy.context.view_layer.objects.active
		if mesh.getName():
			newMeshObject.name = f"{mainName}_{mesh.getName()}"
		else:
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
			meshData.calc_normals_split()
		if mesh.hasColours():
			for layer in mesh.getColourLayerList():
				meshColours = mesh.getVertexColoursLayer(layer)
				newColoursLayer = meshData.color_attributes.new("VertexColours"+str(layer+1),"FLOAT_COLOR","POINT") # BYTE_COLOR *should* be correct, but in practice it isn't
				for i in range(len(meshColours)):
					newColoursLayer.data[i].color = [c/255.0 for c in meshColours[i]]
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
				weightSetData = weightSets[weightIndex]
				for j in range(len(weightSetData[0])):
					groupIndex = weightSetData[0][j]
					groupValue = weightSetData[1][j]
					if groupValue == 0: continue
					vertexGroup = newMeshObject.vertex_groups[groupIndex]
					vertexesToAdd = vertexesInEachSet[weightIndex]
					vertexIDsToAdd = [v.getIndex() for v in vertexesToAdd]
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
		if materials and not context.scene.monado_forge_import.skipMaterialImport and mesh.getMaterialIndex() != -1:
			meshData.materials.append(newMatsByIndex[mesh.getMaterialIndex()])
		
		# import complete, cleanup time
		cleanup_mesh(context,newMeshObject,
						context.scene.monado_forge_import.cleanupLooseVertices,
						context.scene.monado_forge_import.cleanupEmptyGroups,
						context.scene.monado_forge_import.cleanupEmptyColours,
						context.scene.monado_forge_import.cleanupEmptyShapes)
		#meshData.validate(verbose=True)
		meshData.validate()
		meshData.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix().to_4x4(),shape_keys=True) # transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
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