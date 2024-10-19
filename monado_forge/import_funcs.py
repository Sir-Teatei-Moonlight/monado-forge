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
				"CombineNormals":["ReorientNormalMap"],
				"TexInset":["TBNMatrix"],
				}
	if bpy.app.version < (3,4,0):
		prereqs["UVPreProcess"] = ["MixFloats"]
	try:
		for pr in prereqs[nodeId]:
			if pr not in bpy.data.node_groups:
				import_library_node(pr,self,context)
	except KeyError: # no prereqs
		pass
	if nodeId == "BasicMetallic":
		nodeGroup = bpy.data.node_groups.new("BasicMetallic","ShaderNodeTree")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Base Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Ambient Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Emit Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Normal Map")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Alpha")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","AO")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Metallic")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Glossiness")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Emit")
		newNodeGroupOutput(nodeGroup,"NodeSocketShader","BSDF")
		getNodeGroupInput(nodeGroup,"Base Colour").default_value = (0.5,0.5,0.5,1.0)
		getNodeGroupInput(nodeGroup,"Ambient Colour").default_value = (0.0,0.0,0.0,1.0)
		getNodeGroupInput(nodeGroup,"Emit Colour").default_value = (0.0,0.0,0.0,1.0)
		getNodeGroupInput(nodeGroup,"Normal Map").default_value = (0.5,0.5,1.0,1.0)
		getNodeGroupInput(nodeGroup,"Alpha").default_value = 1.0
		getNodeGroupInput(nodeGroup,"AO").default_value = 1.0
		getNodeGroupInput(nodeGroup,"Metallic").default_value = 0.0
		getNodeGroupInput(nodeGroup,"Glossiness").default_value = 0.5
		getNodeGroupInput(nodeGroup,"Emit").default_value = 0.0
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
		if bpy.app.version >= (4,0,0):
			nodeGroup.links.new(metalInput.outputs["Emit Colour"],shaderNode.inputs["Emission Color"])
		else:
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
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Base Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Specular Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Ambient Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Emit Colour")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Normal Map")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Alpha")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","AO")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Glossiness")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Emit")
		newNodeGroupOutput(nodeGroup,"NodeSocketShader","BSDF")
		getNodeGroupInput(nodeGroup,"Base Colour").default_value = (0.5,0.5,0.5,1.0)
		getNodeGroupInput(nodeGroup,"Specular Colour").default_value = (1.0,1.0,1.0,1.0)
		getNodeGroupInput(nodeGroup,"Emit Colour").default_value = (0.0,0.0,0.0,1.0)
		getNodeGroupInput(nodeGroup,"Normal Map").default_value = (0.5,0.5,1.0,1.0)
		getNodeGroupInput(nodeGroup,"Alpha").default_value = 1.0
		getNodeGroupInput(nodeGroup,"AO").default_value = 1.0
		getNodeGroupInput(nodeGroup,"Glossiness").default_value = 0.5
		getNodeGroupInput(nodeGroup,"Emit").default_value = 0.0
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
	elif nodeId == "CombineNormals":
		nodeGroup = bpy.data.node_groups.new("CombineNormals","ShaderNodeTree")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Base")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Overlay")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Factor")
		newNodeGroupOutput(nodeGroup,"NodeSocketColor","Combined")
		getNodeGroupInput(nodeGroup,"Base").default_value = (0.5,0.5,1.0,1.0)
		getNodeGroupInput(nodeGroup,"Overlay").default_value = (0.5,0.5,1.0,1.0)
		getNodeGroupInput(nodeGroup,"Factor").default_value = 1.0
		combineN = nodeGroup.nodes
		combineInput = combineN.new("NodeGroupInput")
		combineInput.location = [-500,0]
		combineOutput = combineN.new("NodeGroupOutput")
		combineOutput.location = [500,0]
		mixNode = combineN.new("ShaderNodeMixRGB")
		mixNode.blend_type = "MIX"
		mixNode.location = [-200,0]
		mixNode.inputs["Color1"].default_value = [0.5,0.5,1.0,1.0]
		mixNode.inputs["Color2"].default_value = [0.5,0.5,1.0,1.0]
		rnmNode = combineN.new("ShaderNodeGroup")
		rnmNode.node_tree = bpy.data.node_groups["ReorientNormalMap"]
		rnmNode.location = [200,0]
		nodeGroup.links.new(combineInput.outputs["Base"],rnmNode.inputs["Base"])
		nodeGroup.links.new(combineInput.outputs["Overlay"],mixNode.inputs["Color2"])
		nodeGroup.links.new(combineInput.outputs["Factor"],mixNode.inputs["Fac"])
		nodeGroup.links.new(mixNode.outputs[0],rnmNode.inputs["Overlay"])
		nodeGroup.links.new(rnmNode.outputs["Combined"],combineOutput.inputs["Combined"])
	elif nodeId == "MixFloats": # ShaderNodeMix for floats doesn't exist in 3.3.1, so gotta make a stand-in
		nodeGroup = bpy.data.node_groups.new("MixFloats","ShaderNodeTree")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Factor")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","A")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","B")
		newNodeGroupOutput(nodeGroup,"NodeSocketFloat","Result")
		getNodeGroupInput(nodeGroup,"Factor").default_value = 0.5
		getNodeGroupInput(nodeGroup,"A").default_value = 0.0
		getNodeGroupInput(nodeGroup,"B").default_value = 0.0
		mixN = nodeGroup.nodes
		mixInput = mixN.new("NodeGroupInput")
		mixInput.location = [-500,0]
		mixOutput = mixN.new("NodeGroupOutput")
		mixOutput.location = [300,0]
		invertNode = mixN.new("ShaderNodeMath")
		invertNode.operation = "SUBTRACT"
		invertNode.inputs[0].default_value = 1.0
		invertNode.location = [-300,0]
		facANode = mixN.new("ShaderNodeMath")
		facANode.operation = "MULTIPLY"
		facANode.location = [-100,100]
		facBNode = mixN.new("ShaderNodeMath")
		facBNode.operation = "MULTIPLY"
		facBNode.location = [-100,-100]
		mergeNode = mixN.new("ShaderNodeMath")
		mergeNode.operation = "ADD"
		mergeNode.location = [100,0]
		nodeGroup.links.new(mixInput.outputs["Factor"],invertNode.inputs[1])
		nodeGroup.links.new(invertNode.outputs["Value"],facANode.inputs[0])
		nodeGroup.links.new(mixInput.outputs["A"],facANode.inputs[1])
		nodeGroup.links.new(mixInput.outputs["Factor"],facBNode.inputs[0])
		nodeGroup.links.new(mixInput.outputs["B"],facBNode.inputs[1])
		nodeGroup.links.new(facANode.outputs["Value"],mergeNode.inputs[0])
		nodeGroup.links.new(facBNode.outputs["Value"],mergeNode.inputs[1])
		nodeGroup.links.new(mergeNode.outputs["Value"],mixOutput.inputs["Result"])
	elif nodeId == "ReorientNormalMap":
		# https://blog.selfshadow.com/publications/blending-in-detail/
		nodeGroup = bpy.data.node_groups.new("ReorientNormalMap","ShaderNodeTree")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Base")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Overlay")
		newNodeGroupOutput(nodeGroup,"NodeSocketColor","Combined")
		getNodeGroupInput(nodeGroup,"Base").default_value = (0.5,0.5,1.0,1.0)
		getNodeGroupInput(nodeGroup,"Overlay").default_value = (0.5,0.5,1.0,1.0)
		combineN = nodeGroup.nodes
		combineInput = combineN.new("NodeGroupInput")
		combineInput.location = [-500,0]
		combineOutput = combineN.new("NodeGroupOutput")
		combineOutput.location = [500,0]
		baseTransformNode = combineN.new("ShaderNodeVectorMath")
		baseTransformNode.operation = "MULTIPLY_ADD"
		baseTransformNode.location = [-300,275]
		baseTransformNode.inputs[1].default_value = [2.0,2.0,2.0]
		baseTransformNode.inputs[2].default_value = [-1.0,-1.0,0.0]
		overlayTransformNode = combineN.new("ShaderNodeVectorMath")
		overlayTransformNode.operation = "MULTIPLY_ADD"
		overlayTransformNode.location = [-300,0]
		overlayTransformNode.inputs[1].default_value = [-2.0,-2.0,2.0]
		overlayTransformNode.inputs[2].default_value = [1.0,1.0,-1.0]
		dotNode = combineN.new("ShaderNodeVectorMath")
		dotNode.operation = "DOT_PRODUCT"
		dotNode.location = [-100,175]
		scaleNode1 = combineN.new("ShaderNodeVectorMath")
		scaleNode1.operation = "SCALE"
		scaleNode1.location = [-100,25]
		splitNode = combineN.new("ShaderNodeSeparateXYZ")
		splitNode.location = [-100,-125]
		scaleNode2 = combineN.new("ShaderNodeVectorMath")
		scaleNode2.operation = "SCALE"
		scaleNode2.location = [100,-125]
		subtractNode = combineN.new("ShaderNodeVectorMath")
		subtractNode.operation = "SUBTRACT"
		subtractNode.location = [100,175]
		normalizeNode = combineN.new("ShaderNodeVectorMath")
		normalizeNode.operation = "NORMALIZE"
		normalizeNode.location = [100,25]
		finalTransformNode = combineN.new("ShaderNodeVectorMath")
		finalTransformNode.operation = "MULTIPLY_ADD"
		finalTransformNode.location = [300,75]
		finalTransformNode.inputs[1].default_value = [0.5,0.5,0.5]
		finalTransformNode.inputs[2].default_value = [0.5,0.5,0.5]
		nodeGroup.links.new(combineInput.outputs["Base"],baseTransformNode.inputs[0])
		nodeGroup.links.new(combineInput.outputs["Overlay"],overlayTransformNode.inputs[0])
		nodeGroup.links.new(baseTransformNode.outputs[0],dotNode.inputs[0])
		nodeGroup.links.new(overlayTransformNode.outputs[0],dotNode.inputs[1])
		nodeGroup.links.new(baseTransformNode.outputs[0],scaleNode1.inputs[0])
		nodeGroup.links.new(dotNode.outputs["Value"],scaleNode1.inputs["Scale"])
		nodeGroup.links.new(baseTransformNode.outputs[0],splitNode.inputs[0])
		nodeGroup.links.new(overlayTransformNode.outputs[0],scaleNode2.inputs[0])
		nodeGroup.links.new(splitNode.outputs["Z"],scaleNode2.inputs["Scale"])
		nodeGroup.links.new(scaleNode1.outputs[0],subtractNode.inputs[0])
		nodeGroup.links.new(scaleNode2.outputs[0],subtractNode.inputs[1])
		nodeGroup.links.new(subtractNode.outputs[0],normalizeNode.inputs[0])
		nodeGroup.links.new(normalizeNode.outputs[0],finalTransformNode.inputs[0])
		nodeGroup.links.new(finalTransformNode.outputs[0],combineOutput.inputs["Combined"])
	elif nodeId == "TBNMatrix":
		# https://blender.stackexchange.com/questions/291989/how-would-i-get-the-full-tbn-matrix-from-just-a-normal-map
		nodeGroup = bpy.data.node_groups.new("TBNMatrix","ShaderNodeTree")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Normal Map")
		newNodeGroupInput(nodeGroup,"NodeSocketVector","Tangent")
		newNodeGroupOutput(nodeGroup,"NodeSocketVector","Tangent")
		newNodeGroupOutput(nodeGroup,"NodeSocketVector","Bitangent")
		newNodeGroupOutput(nodeGroup,"NodeSocketVector","Normal")
		getNodeGroupInput(nodeGroup,"Normal Map").default_value = (0.5,0.5,1.0,1.0)
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
		newNodeGroupInput(nodeGroup,"NodeSocketVector","UV")
		newNodeGroupInput(nodeGroup,"NodeSocketVector","Tangent")
		newNodeGroupInput(nodeGroup,"NodeSocketColor","Normal Map")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Depth")
		newNodeGroupOutput(nodeGroup,"NodeSocketVector","UV")
		getNodeGroupInput(nodeGroup,"Normal Map").default_value = (0.5,0.5,1.0,1.0)
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
	elif nodeId == "UVPreProcess":
		nodeGroup = bpy.data.node_groups.new("UVPreProcess","ShaderNodeTree")
		newNodeGroupInput(nodeGroup,"NodeSocketVector","Vector")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Is U Clamp") # would prefer NodeSocketBool but that doesn't seem to work as expected
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Is V Clamp")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Is U Mirror")
		newNodeGroupInput(nodeGroup,"NodeSocketFloat","Is V Mirror")
		newNodeGroupOutput(nodeGroup,"NodeSocketVector","Vector")
		preproN = nodeGroup.nodes
		preproInput = preproN.new("NodeGroupInput")
		preproInput.location = [-800,0]
		preproOutput = preproN.new("NodeGroupOutput")
		preproOutput.location = [600,0]
		sepNode = preproN.new("ShaderNodeSeparateXYZ")
		sepNode.location = [-600,0]
		merNode = preproN.new("ShaderNodeCombineXYZ")
		merNode.location = [400,0]
		clampUNode = preproN.new("ShaderNodeClamp")
		clampUNode.inputs["Min"].default_value = 0.0
		clampUNode.inputs["Max"].default_value = 1.0
		clampUNode.location = [-400,100]
		clampUNode.label = "Clamp U"
		clampVNode = preproN.new("ShaderNodeClamp")
		clampVNode.inputs["Min"].default_value = 0.0
		clampVNode.inputs["Max"].default_value = 1.0
		clampVNode.location = [-400,-100]
		clampVNode.label = "Clamp V"
		mirUNode = preproN.new("ShaderNodeMath")
		mirUNode.operation = "PINGPONG"
		mirUNode.inputs[1].default_value = 1.0 # yay magic numbers (they're all called "Value")
		mirUNode.location = [-200,100]
		mirUNode.label = "Mirror U"
		mirVNode = preproN.new("ShaderNodeMath")
		mirVNode.operation = "PINGPONG"
		mirVNode.inputs[1].default_value = 1.0
		mirVNode.location = [-200,-100]
		mirVNode.label = "Mirror V"
		if bpy.app.version < (3,4,0):
			mixNodeCU = preproN.new("ShaderNodeGroup")
			mixNodeCU.node_tree = bpy.data.node_groups["MixFloats"]
			mixNodeCV = preproN.new("ShaderNodeGroup")
			mixNodeCV.node_tree = bpy.data.node_groups["MixFloats"]
			mixNodeMU = preproN.new("ShaderNodeGroup")
			mixNodeMU.node_tree = bpy.data.node_groups["MixFloats"]
			mixNodeMV = preproN.new("ShaderNodeGroup")
			mixNodeMV.node_tree = bpy.data.node_groups["MixFloats"]
		else:
			mixNodeCU = preproN.new("ShaderNodeMix")
			mixNodeCU.data_type = "FLOAT"
			mixNodeCV = preproN.new("ShaderNodeMix")
			mixNodeCV.data_type = "FLOAT"
			mixNodeMU = preproN.new("ShaderNodeMix")
			mixNodeMU.data_type = "FLOAT"
			mixNodeMV = preproN.new("ShaderNodeMix")
			mixNodeMV.data_type = "FLOAT"
		mixNodeCU.location = [0,100]
		mixNodeCU.label = "Apply U Clamp"
		mixNodeCV.location = [0,-100]
		mixNodeCV.label = "Apply V Clamp"
		mixNodeMU.location = [200,100]
		mixNodeMU.label = "Apply U Mirror"
		mixNodeMV.location = [200,-100]
		mixNodeMV.label = "Apply V Mirror"
		nodeGroup.links.new(preproInput.outputs[0],sepNode.inputs[0])
		nodeGroup.links.new(sepNode.outputs["X"],clampUNode.inputs["Value"])
		nodeGroup.links.new(sepNode.outputs["X"],mirUNode.inputs["Value"])
		nodeGroup.links.new(sepNode.outputs["Y"],clampVNode.inputs["Value"])
		nodeGroup.links.new(sepNode.outputs["Y"],mirVNode.inputs["Value"])
		nodeGroup.links.new(preproInput.outputs[1],mixNodeCU.inputs["Factor"])
		nodeGroup.links.new(preproInput.outputs[2],mixNodeCV.inputs["Factor"])
		nodeGroup.links.new(preproInput.outputs[3],mixNodeMU.inputs["Factor"])
		nodeGroup.links.new(preproInput.outputs[4],mixNodeMV.inputs["Factor"])
		nodeGroup.links.new(sepNode.outputs["X"],mixNodeCU.inputs["A"])
		nodeGroup.links.new(sepNode.outputs["Y"],mixNodeCV.inputs["A"])
		nodeGroup.links.new(mixNodeCU.outputs["Result"],mixNodeMU.inputs["A"])
		nodeGroup.links.new(mixNodeCV.outputs["Result"],mixNodeMV.inputs["A"])
		nodeGroup.links.new(clampUNode.outputs[0],mixNodeCU.inputs["B"])
		nodeGroup.links.new(clampVNode.outputs[0],mixNodeCV.inputs["B"])
		nodeGroup.links.new(mirUNode.outputs[0],mixNodeMU.inputs["B"])
		nodeGroup.links.new(mirVNode.outputs[0],mixNodeMV.inputs["B"])
		nodeGroup.links.new(mixNodeMU.outputs["Result"],merNode.inputs["X"])
		nodeGroup.links.new(mixNodeMV.outputs["Result"],merNode.inputs["Y"])
		nodeGroup.links.new(sepNode.outputs["Z"],merNode.inputs["Z"])
		nodeGroup.links.new(merNode.outputs[0],preproOutput.inputs[0])
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
	compressEDVs = context.scene.monado_forge_import.compressEDVs
	armaturesCreated = 0
	# we create the external armature (if any) first so it gets name priority
	if context.scene.monado_forge_import.importToCursor:
		pos = context.scene.cursor.location
		rot = context.scene.cursor.rotation_euler
	else:
		pos = (0,0,0)
		rot = (0,0,0)
	externalSkeleton = forgeResults.externalSkeleton
	if externalSkeleton:
		armatureName = mainName
		externalArmature = create_armature_from_bones(externalSkeleton,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
		armaturesCreated += 1
	else:
		externalArmature = None
	baseSkeleton = forgeResults.skeleton
	if baseSkeleton:
		armatureName = mainName
		baseArmature = create_armature_from_bones(baseSkeleton,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
		armaturesCreated += 1
	else:
		baseArmature = None
	if printProgress:
		print("Finished creating "+str(armaturesCreated)+" armatures.")
	
	materials = forgeResults.materials
	newMatsByIndex = {}
	for m,mat in enumerate(materials):
		newMat = bpy.data.materials.new(name=mat.name)
		if context.scene.monado_forge_import.fixedViewportColour:
			newMat.diffuse_color = context.scene.monado_forge_import.viewportColour
		else:
			newMat.diffuse_color = mat.viewportColour
		transparencyEnum = ["OPAQUE","CLIP","BLEND"]
		newMat.blend_method = transparencyEnum[mat.transparency]
		shadowTransparencyEnum = ["OPAQUE","CLIP","OPAQUE"] # only binary shadows allowed
		newMat.shadow_method = shadowTransparencyEnum[mat.transparency]
		newMat.use_backface_culling = mat.cullingBack # dunno what to do about any that cull front, so leaving it out
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
				newNodeGroupInput(dummyShader,"NodeSocketColor","Base Color")
				newNodeGroupOutput(dummyShader,"NodeSocketShader","BSDF")
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
		baseColourNode.outputs[0].default_value = mat.baseColour
		baseColourNode.label = "Base Colour"
		baseColourNode.location = [-650,300]
		n.get("Material Output").location = [950,300]
		texNodes = []
		# the setup: these are the "buckets" for what pre-processing must be done to the textures within
		# covers clamp (cu, cv) and mirror (mu, mv, muv)
		# some combos don't make logical sense (e.g. both clamp and mirror on U) but we have them anyway since it's just simpler
		preprocessing = {"":[],"cu":[],"cv":[],"mu":[],"cumu":[],"cvmu":[],"mv":[],"cumv":[],"cvmv":[],"muv":[],"cumuv":[],"cvmuv":[]}
		if createDummyShader and not mat.textures: # no textures, plug in the base colour directly
			newMat.node_tree.links.new(baseColourNode.outputs[0],shaderSubnode.inputs["Base Color"])
		for ti,t in enumerate(mat.textures):
			currentPreprocess = ""
			texNode = n.new("ShaderNodeTexImage")
			# Blender no longer supports mixed cases of extend vs. repeat
			# so while we can just set the texture if both are the same, we need to preprocess if they aren't
			texNode.extension = "EXTEND"
			repeat = t.repeating
			if repeat[0] or repeat[1]:
				texNode.extension = "REPEAT"
			if repeat[0] != repeat[1]:
				currentPreprocess += "cu" if repeat[1] else "cv"
			texNode.interpolation = "Closest"
			if t.isFiltered:
				texNode.interpolation = "Linear"
			texNode.image = bpy.data.images[t.name]
			# use the name to guess what should be non-colour data
			if any([
				"_NRM" in t.name,"_NML" in t.name, # normal
				"_MTL" in t.name, # metal
				"_SHY" in t.name, # gloss
				"_ALP" in t.name, # alpha
				"_AO" in t.name, # ambient occlusion
				"_GLO" in t.name, # glow/emit
				"_MSK" in t.name, # mask
				"_VEL" in t.name, # velocity (fur/hair map)
				"_DPS" in t.name, # displacement?
				"temp" in t.name, # channelised
				]):
					texNode.image.colorspace_settings.name = "Non-Color"
			tx = ti%4
			ty = ti//4
			texNode.location = [tx*250-325,ty*-250+300]
			# guess: the first texture is the base colour
			if ti == 0 and createDummyShader:
				newMat.node_tree.links.new(texNode.outputs["Color"],shaderSubnode.inputs["Base Color"])
			mir = t.mirroring
			mU = "u" if mir[0] else ""
			mV = "v" if mir[1] else ""
			if mU+mV != "":
				currentPreprocess += "m"+mU+mV
			# for temp files, add a colour splitter for convenience
			if "temp" in t.name:
				sepNode = n.new("ShaderNodeSeparateColor")
				sepNode.location = texNode.location + mathutils.Vector([125,-25])
				sepNode.hide = True
				newMat.node_tree.links.new(texNode.outputs["Color"],sepNode.inputs[0])
			preprocessing[currentPreprocess].append(texNode)
		colourCount = mat.colourLayerCount # this will probably result in overestimation, but that's okay
		uvCount = mat.uvLayerCount # same
		pushdownValue = 100 # to keep track of node posititon across multiple for loops
		# we do UVs first because the node is shorter and they're more common than colours
		for uv in range(uvCount):
			uvInputNode = n.new("ShaderNodeUVMap")
			uvInputNode.label = "UV Map "+str(uv+1)
			uvInputNode.hide = True
			uvInputNode.location = [-650,pushdownValue]
			uvInputNode.uv_map = "UV"+str(uv+1)
			pushdownValue -= 40
			if not mat.textures or preprocessing[""]: # no textures means no preprocessing defined: assume none
				if uv == 0:
					for texNode in preprocessing[""]:
						newMat.node_tree.links.new(uvInputNode.outputs["UV"],texNode.inputs["Vector"])
			for ppType in preprocessing.keys():
				if ppType == "": continue
				if preprocessing[ppType]: # if not empty, make a node for it, and attach the contained textures to it
					try:
						ppNodeGroup = bpy.data.node_groups["UVPreProcess"]
					except KeyError:
						import_library_node("UVPreProcess", self, context)
						ppNodeGroup = bpy.data.node_groups["UVPreProcess"]
					ppNode = n.new("ShaderNodeGroup")
					ppNode.node_tree = ppNodeGroup
					ppNode.location = [-650,pushdownValue]
					pushdownValue -= 40
					ppNode.hide = True
					ppNode.label = ""
					if "cu" in ppType:
						ppNode.inputs["Is U Clamp"].default_value = 1.0
						ppNode.label += "ClampU"
					if "cv" in ppType:
						ppNode.inputs["Is V Clamp"].default_value = 1.0
						ppNode.label += "ClampV"
					if "mu" in ppType or "muv" in ppType: # sure it's redundant, but to be 100% clear
						ppNode.inputs["Is U Mirror"].default_value = 1.0
						ppNode.label += "MirrorU"
					if "mv" in ppType or "muv" in ppType: # sure it's redundant, but to be 100% clear
						ppNode.inputs["Is V Mirror"].default_value = 1.0
						ppNode.label += "MirrorV"
					for texNode in preprocessing[ppType]:
						newMat.node_tree.links.new(uvInputNode.outputs["UV"],ppNode.inputs[0])
						if uv == 0:
							newMat.node_tree.links.new(ppNode.outputs[0],texNode.inputs["Vector"])
		for colour in range(colourCount):
			colourInputNode = n.new("ShaderNodeAttribute")
			colourInputNode.label = "Vertex Colours "+str(colour+1)
			colourInputNode.location = [-650,pushdownValue]
			colourInputNode.attribute_type = "GEOMETRY"
			colourInputNode.attribute_name = "VertexColours"+str(colour+1)
			colourInputNode.hide = True
			pushdownValue -= 40
		for xi,x in enumerate(mat.extraData):
			extraDataNode = n.new("ShaderNodeValue")
			extraDataNode.outputs["Value"].default_value = x
			if compressEDVs:
				extraDataNode.label = "EDV["+str(xi)+"] = "+str(x)
				extraDataNode.location = [-475,xi*-35+300]
				extraDataNode.hide = True
			else:
				extraDataNode.label = "Extra Data Value ["+str(xi)+"]"
				extraDataNode.location = [-475,xi*-100+300]
		newMatsByIndex[mat.index] = newMat
	
	meshes = forgeResults.meshes
	for m,mesh in enumerate(meshes):
		if printProgress:
			print_progress_bar(m,len(meshes),"Mesh creation")
		bpy.ops.object.add(type="MESH", enter_editmode=False, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
		newMeshObject = bpy.context.view_layer.objects.active
		if mesh.name:
			newMeshObject.name = f"{mainName}_{mesh.name}"
		else:
			newMeshObject.name = f"{mainName}_mesh{m:03d}"
		meshData = newMeshObject.data
		meshData.name = "Mesh"
		vertCount = len(mesh.vertices)
		meshData.from_pydata(mesh.getVertexPositionsList(),[],mesh.getFaceVertexIndexesList())
		for f in meshData.polygons:
			f.use_smooth = True
		if bpy.app.version < (4,1,0): # 4.1 removed this and made it the default (kind of)
			meshData.use_auto_smooth = True
		if mesh.hasWeightIndexes() and baseArmature: # try the indexes method first (faster) (and also needs a baseArmature or it makes no sense)
			weightIndexes = set(mesh.getVertexWeightIndexesList())
			vertexesInEachGroup = {}
			for i in range(len(baseArmature.data.bones)):
				newMeshObject.vertex_groups.new(name=baseArmature.data.bones[i].name)
				vertexesInEachGroup[i] = mesh.getVertexesInWeightGroup(i)
			vertexesInEachSet = {}
			for i in weightIndexes:
				vertexesInEachSet[i] = mesh.getVertexesWithWeightIndex(i)
			weightSets = mesh.weightSets
			for weightIndex in weightIndexes:
				weightSetData = weightSets[weightIndex]
				for j in range(len(weightSetData[0])):
					groupIndex = weightSetData[0][j]
					groupValue = weightSetData[1][j]
					if groupValue == 0: continue
					vertexGroup = newMeshObject.vertex_groups[groupIndex]
					vertexesToAdd = vertexesInEachSet[weightIndex]
					vertexIDsToAdd = [v.index for v in vertexesToAdd]
					newMeshObject.vertex_groups[groupIndex].add(vertexIDsToAdd,groupValue,"ADD")
		elif mesh.hasWeights(): # no indexes, but do have directly-applied weights
			pass # not needed at the present time
		if mesh.hasNormals():
			normalsList = mesh.getLoopNormalsList()
			meshData.normals_split_custom_set(normalsList)
			if bpy.app.version < (4,1,0): # function removed, no longer needed
				meshData.calc_normals_split()
		if mesh.hasColours():
			meshColours = mesh.getLoopColoursList()
			for layer,colours in meshColours.items():
				newColoursLayer = meshData.color_attributes.new("VertexColours"+str(layer+1),"FLOAT_COLOR","CORNER") # BYTE_COLOR *should* be correct, but in practice it isn't
				for loop in meshData.loops:
					newColoursLayer.data[loop.index].color = [toBlenderColour_255(c) for c in colours[loop.index]]
		if mesh.hasUVs():
			meshUVs = mesh.getLoopUVsList()
			for layer,uvs in meshUVs.items():
				newUVsLayer = meshData.uv_layers.new(name="UV"+str(layer+1))
				for loop in meshData.loops:
					newUVsLayer.data[loop.index].uv = uvs[loop.index]
		if mesh.hasOutlines():
			meshOutlines = mesh.getLoopOutlinesList()
			# since vertex alpha is not a logical place for Blender to look for outline thickness,
			# we move it to a new vertex group instead
			newColoursLayer = meshData.color_attributes.new("OutlineColours","FLOAT_COLOR","CORNER") # BYTE_COLOR *should* be correct, but in practice it isn't
			thicknessGroup = newMeshObject.vertex_groups.new(name="OutlineThickness")
			for loop in meshData.loops:
				thickness = meshOutlines[loop.index][3]/255.0
				thisColour = [toBlenderColour_255(c) for c in meshOutlines[loop.index]]
				thisColour[3] = 1.0 # cancel using alpha for thickness
				newColoursLayer.data[loop.index].color = thisColour
				thicknessGroup.add([loop.vertex_index],thickness,"REPLACE") # hopefully we don't end up with a vertex that requires multiple different thicknesses...
			outlineMod = newMeshObject.modifiers.new(name="Outline",type="SOLIDIFY")
			outlineMod.use_rim = False
			outlineMod.use_flip_normals = True
			outlineMod.thickness  = context.scene.monado_forge_import.maxOutlineThickness
			outlineMod.offset = 1
			outlineMod.vertex_group = "OutlineThickness"
			outlineMod.thickness_vertex_group = context.scene.monado_forge_import.minOutlineFactor/100.0 # min value for thickness 0 (percentage in the UI, hence the /100.0)
			outlineMod.material_offset = 1
		if mesh.hasShapes():
			shapes = mesh.shapes
			if not meshData.shape_keys:
				newMeshObject.shape_key_add(name="basis",from_mix=False)
			meshData.shape_keys.use_relative = True
			for s in shapes:
				newShape = newMeshObject.shape_key_add(name=s.name,from_mix=False)
				for vertexIndex,vertex in s.vertices.items():
					newShape.data[vertexIndex].co += mathutils.Vector(vertex.position)
		if materials and not context.scene.monado_forge_import.skipMaterialImport and mesh.materialIndex != -1:
			meshData.materials.append(newMatsByIndex[mesh.materialIndex])
		
		# import complete, cleanup time
		cleanup_mesh(context,newMeshObject,
						context.scene.monado_forge_import.cleanupLooseVertices,
						context.scene.monado_forge_import.cleanupEmptyGroups,
						context.scene.monado_forge_import.cleanupEmptyColours,
						context.scene.monado_forge_import.cleanupEmptyOutlines,
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