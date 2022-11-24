import bpy
#import math
#import mathutils
import os
import traceback
from bpy.props import (
						BoolProperty,
#						EnumProperty,
#						FloatProperty,
						PointerProperty,
						StringProperty,
						)
from bpy.types import (
						Operator,
						Panel,
						PropertyGroup,
						)

from . utils import *

def import_wimdo(f):
	# little endian assumed
	magic = f.read(4)
	if magic != b"DMXM":
		self.report({"ERROR"}, "Not a valid .wimdo file (unexpected header)")
		return {"CANCELLED"}
	version = readAndParseInt(f,4)
	meshesOffset = readAndParseInt(f,4)
	materialsOffset = readAndParseInt(f,4)
	unknown1 = readAndParseInt(f,4)
	vertexBufferOffset = readAndParseInt(f,4)
	shadersOffset = readAndParseInt(f,4)
	cachedTexturesTableOffset = readAndParseInt(f,4)
	unknown2 = readAndParseInt(f,4)
	uncachedTexturesTableOffset = readAndParseInt(f,4)
	
	forgeBones = []
	
	if meshesOffset > 0:
		f.seek(meshesOffset)
		meshesUnknown1 = readAndParseInt(f,4)
		boundingBoxStart = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
		boundingBoxEnd = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
		meshDataOffset = readAndParseInt(f,4)
		meshCount = readAndParseInt(f,4)
		meshesUnknown2 = readAndParseInt(f,4)
		bonesOffset = readAndParseInt(f,4)
		f.seek(meshesOffset+21*4) # skip these unknowns
		shapesOffset = readAndParseInt(f,4)
		shapeNamesOffset = readAndParseInt(f,4)
		f.seek(meshesOffset+21*4) # skip s'more
		lodsOffset = readAndParseInt(f,4)
		
		if meshCount > 0:
			f.seek(meshesOffset+meshDataOffset)
			# [...]
		if bonesOffset > 0:
			f.seek(meshesOffset+bonesOffset)
			boneCount = readAndParseInt(f,4)
			boneCount2 = readAndParseInt(f,4)
			boneHeaderOffset = readAndParseInt(f,4)
			boneMatrixesOffset = readAndParseInt(f,4)
			bonesUnknown1 = readAndParseInt(f,4)
			bonesUnknown2 = readAndParseInt(f,4) # claimed by XBC2MD to be "positions offset", but that's part of the matrixes
			bonePairsOffset = readAndParseInt(f,4)
			
			for b in range(boneCount):
				f.seek(meshesOffset+bonesOffset+boneHeaderOffset+b*6*4)
				nameOffset = readAndParseInt(f,4)
				boneUnknown1 = readAndParseInt(f,4)
				boneType = readAndParseInt(f,4)
				boneIndex = readAndParseInt(f,4)
				f.seek(meshesOffset+bonesOffset+nameOffset)
				boneName = readStr(f)
				f.seek(meshesOffset+bonesOffset+boneMatrixesOffset+b*16*4)
				boneXAxis = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
				boneYAxis = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
				boneZAxis = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
				bonePosition = [-readAndParseFloat(f),-readAndParseFloat(f),-readAndParseFloat(f),-readAndParseFloat(f)] # yes, the negatives are needed
				# the position needs to be modified by the matrix in order to place it as expected
				posMatrix = mathutils.Matrix.Translation(bonePosition)
				rotMatrix = mathutils.Matrix([boneXAxis,boneYAxis,boneZAxis,bonePosition])
				bonePosition = (rotMatrix @ posMatrix).to_translation().to_4d()
				fb = MonadoForgeBone()
				fb.setName(boneName)
				fb.setPos(bonePosition[:]) # the [:] is because we're turning a Vector into a list
				fb.setRot(rotMatrix.to_quaternion())
				forgeBones.append(fb)
	
	if materialsOffset > 0:
		f.seek(materialsOffset)
	if vertexBufferOffset > 0:
		f.seek(vertexBufferOffset)
	if shadersOffset > 0:
		f.seek(shadersOffset)
	if cachedTexturesTableOffset > 0:
		f.seek(cachedTexturesTableOffset)
	if uncachedTexturesTableOffset > 0:
		f.seek(uncachedTexturesTableOffset)
	
	results = MonadoForgePackage()
	results.setBones(forgeBones)
	return results

def import_wimdo_only(self, context):
	absoluteDefsPath = bpy.path.abspath(context.scene.xb_tools_model.defsPath)
	print("Importing model from: "+absoluteDefsPath)
	
	if os.path.splitext(absoluteDefsPath)[1] != ".wimdo":
		self.report({"ERROR"}, "File was not a .wimdo file")
		return {"CANCELLED"}
	
	with open(absoluteDefsPath, "rb") as f:
		forgeResults = import_wimdo(f)
	realise_results(forgeResults,context)
	return {"FINISHED"}

def import_wismt_only(self, context):
	self.report({"ERROR"}, "Importing a .wismt only not yet supported")
	return {"CANCELLED"}

def import_wimdo_and_wismt(self, context):
	absoluteDefsPath = bpy.path.abspath(context.scene.xb_tools_model.defsPath)
	absoluteDataPath = bpy.path.abspath(context.scene.xb_tools_model.dataPath)
	print("Importing model from: "+absoluteDefsPath+" & "+absoluteDataPath)
	
	if os.path.splitext(absoluteDefsPath)[1] != ".wimdo":
		self.report({"ERROR"}, "First file was not a .wimdo file")
		return {"CANCELLED"}
	if os.path.splitext(absoluteDefsPath)[1] != ".wismt":
		self.report({"ERROR"}, "Second file was not a .wismt file")
		return {"CANCELLED"}
	
	with open(absoluteDefsPath, "rb") as f:
		forgeResults = import_wimdo(f)
	realise_results(forgeResults,context)
	
	return {"FINISHED"}

def realise_results(forgeResults,context):
	skeleton = forgeResults.getBones()
	armatureName = skeleton[0].getName()
	if context.scene.xb_tools_model.useSkeletonSettings:
		boneSize = context.scene.xb_tools_skeleton.boneSize
		positionEpsilon = context.scene.xb_tools_skeleton.positionEpsilon
		angleEpsilon = context.scene.xb_tools_skeleton.angleEpsilon
	else:
		boneSize = 0.1
		positionEpsilon = 0.0001
		angleEpsilon = math.radians(0.1)
	create_armature_from_bones(skeleton,armatureName,boneSize,positionEpsilon,angleEpsilon)
	# bpy.ops.object.add(type="MESH", enter_editmode=False, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
	# newObject = bpy.context.view_layer.objects.active
	# newObject.name = "Mesh"
	# mesh = newObject.data
	# mesh.name = "Mesh"
	# mesh.from_pydata([(0,0,0)],[],[])

class XBModelImportOperator(Operator):
	bl_idname = "object.xb_tools_model_operator"
	bl_label = "Xenoblade Model Import Operator"
	bl_description = "Imports a model from a Xenoblade file"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		return context.scene.xb_tools_model.singlePath or context.scene.xb_tools_model.defsPath or context.scene.xb_tools_model.dataPath
	
	def execute(self, context):
		try:
			game = context.scene.xb_tools.game
			if game == "XC1" or game == "XCX":
				self.report({"ERROR"}, "game not yet supported")
				return {"CANCELLED"}
			if context.scene.xb_tools_model.defsPath and context.scene.xb_tools_model.dataPath:
				return import_wimdo_and_wismt(self, context)
			elif context.scene.xb_tools_model.defsPath:
				return import_wimdo_only(self, context)
			elif context.scene.xb_tools_model.dataPath:
				return import_wismt_only(self, context)
			self.report({"ERROR"}, "Unexpected error; code shouldn't be able to reach here")
			return {"CANCELLED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class XBModelToolsProperties(PropertyGroup):
	singlePath : StringProperty(
		name="Path",
		description="File to import",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	defsPath : StringProperty(
		name="Definition Path",
		description="Definitions file to import",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	dataPath : StringProperty(
		name="Data Path",
		description="Data file to import",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	useSkeletonSettings : BoolProperty(
		name="Use Skeleton Settings",
		description="If model contains any bones, use settings from the Skeleton panel to import it (false: use default settings)",
		default=True,
	)

class OBJECT_PT_XBModelToolsPanel(Panel):
	bl_idname = "OBJECT_PT_XBModelToolsPanel"
	bl_label = "Mesh"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_XBToolsPanel"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		activeObject = bpy.context.view_layer.objects.active
		col = layout.column(align=True)
		importPanel = col.column(align=True)
		importPanel.label(text="Import")
		if scn.xb_tools.game == "XC1":
			importPanel.prop(scn.xb_tools_model, "singlePath", text=".brres")
		else:
			defsRow = importPanel.row()
			defsRow.prop(scn.xb_tools_model, "defsPath", text=".wimdo")
			#dataRow = importPanel.row()
			#dataRow.prop(scn.xb_tools_model, "dataPath", text=".wismt")
		importPanel.prop(scn.xb_tools_model, "useSkeletonSettings")
		importPanel.operator(XBModelImportOperator.bl_idname, text="Import Model", icon="IMPORT")

classes = (
			XBModelImportOperator,
			XBModelToolsProperties,
			OBJECT_PT_XBModelToolsPanel,
			)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

	bpy.types.Scene.xb_tools_model = PointerProperty(type=XBModelToolsProperties)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.xb_tools_model

#[...]