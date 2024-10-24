import bpy
import math
import mathutils
import os
import traceback
from bpy.props import (
						BoolProperty,
						EnumProperty,
						FloatProperty,
						FloatVectorProperty,
						IntProperty,
						PointerProperty,
						StringProperty,
						)
from bpy.types import (
						Operator,
						Panel,
						PropertyGroup,
						)

from . classes import *
from . utils import *
from . import_funcs import *
from . import_funcs_brres import *
from . import_funcs_sar1 import *

class MonadoForgeViewImportSkeletonOperator(Operator):
	bl_idname = "object.monado_forge_skeleton_import_operator"
	bl_label = "Xenoblade Skeleton Import Operator"
	bl_description = "Imports a skeleton from a Xenoblade file"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		return context.scene.monado_forge_import.skeletonPath
	
	def execute(self, context):
		try:
			game = context.scene.monado_forge_main.game
			if game == "XC1":
				self.report({"ERROR"}, ".brres format shouldn't be able to call this function")
				return {"CANCELLED"}
			printProgress = context.scene.monado_forge_main.printProgress
			absolutePath = bpy.path.abspath(context.scene.monado_forge_import.skeletonPath)
			if printProgress:
				print("Importing skeleton from: "+absolutePath)
			
			filename, fileExtension = os.path.splitext(absolutePath)
			expectedExtension = {"XCX":".xcx","XC2":".arc","XC1DE":".chr","XC3":".chr",}[game]
			if fileExtension != expectedExtension:
				self.report({"ERROR"}, "Unexpected file type (for "+game+", expected "+expectedExtension+")")
				return {"CANCELLED"}
			
			# first, read in the data and store it in a game-agnostic way
			if game == "XCX": # big endian
				modelFormat = "[xcx]"
			elif game == "XC2":
				modelFormat = "SAR1"
			elif game == "XC1DE":
				modelFormat = "SAR1"
			elif game == "XC3":
				modelFormat = "SAR1"
			
			if modelFormat == "BRES":
				self.report({"ERROR"}, ".brres format not yet supported")
				return {"CANCELLED"}
			elif modelFormat == ".xcx":
				self.report({"ERROR"}, "(whatever XCX uses) format not yet supported")
				return {"CANCELLED"}
			elif modelFormat == "SAR1":
				return import_sar1_skeleton_only(self, context)
			else:
				self.report({"ERROR"}, "Unknown format: "+modelFormat)
				return {"CANCELLED"}
			
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeViewImportModelOperator(Operator):
	bl_idname = "object.monado_forge_model_import_operator"
	bl_label = "Xenoblade Model Import Operator"
	bl_description = "Imports a model from a Xenoblade file"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		# can't import a .wismt without a .wimdo (requires vertex table + face table alignment)
		return context.scene.monado_forge_import.singlePath or context.scene.monado_forge_import.defsPath
	
	def execute(self, context):
		game = context.scene.monado_forge_main.game
		if game == "XC1":
			self.report({"ERROR"}, ".brres format shouldn't be able to call this function")
			return {"CANCELLED"}
		# this isn't part of the poll because it's not a trivial check and the fix needs to be more descriptive
		if context.scene.monado_forge_import.autoSaveTextures:
			if not os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.texturePath)):
				self.report({"ERROR"}, "Auto-save selected, but texture output path is not an existing folder")
				return {"CANCELLED"}
		if game == "XC3" and (context.scene.monado_forge_import.importUncachedTextures and
				not (os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.textureRepoMPath)) and os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.textureRepoHPath)))):
			self.report({"ERROR"}, "Import uncached textures selected, but no texture repositories provided (both are required)")
			return {"CANCELLED"}
		try:
			if game == "XCX":
				self.report({"ERROR"}, "game not yet supported")
				return {"CANCELLED"}
			if context.scene.monado_forge_import.defsPath and context.scene.monado_forge_import.dataPath:
				return import_wimdo_and_wismt(self, context)
			elif context.scene.monado_forge_import.defsPath:
				return import_wimdo_only(self, context)
			self.report({"ERROR"}, "Unexpected error; code shouldn't be able to reach here")
			return {"CANCELLED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class MonadoForgeViewImportModelWithSkeletonOperator(Operator):
	bl_idname = "object.monado_forge_model_with_skeleton_import_operator"
	bl_label = "Xenoblade Model With Skeleton Import Operator"
	bl_description = "Imports a model using an external skeleton from a Xenoblade file"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		# require all of .arc/.chr, .wimdo, and .wismt (there are no known situations where a .wimdo with an embedded model has a .arc/.chr but no .wismt)
		return context.scene.monado_forge_import.singlePath or (context.scene.monado_forge_import.skeletonPath and context.scene.monado_forge_import.defsPath and context.scene.monado_forge_import.dataPath)
	
	def execute(self, context):
		game = context.scene.monado_forge_main.game
		# this isn't part of the poll because it's not a trivial check and the fix needs to be more descriptive
		if context.scene.monado_forge_import.autoSaveTextures:
			if not os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.texturePath)):
				self.report({"ERROR"}, "Auto-save selected, but texture output path is not an existing folder")
				return {"CANCELLED"}
		if game == "XC3" and (context.scene.monado_forge_import.importUncachedTextures and
				not (os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.textureRepoMPath)) and os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.textureRepoHPath)))):
			self.report({"ERROR"}, "Import uncached textures selected, but no texture repositories provided (both are required)")
			return {"CANCELLED"}
		
		if game != "XC1":
			filename, fileExtension = os.path.splitext(bpy.path.abspath(context.scene.monado_forge_import.skeletonPath))
			expectedExtension = {"XCX":".xcx","XC2":".arc","XC1DE":".chr","XC3":".chr",}[game]
			if fileExtension != expectedExtension:
				self.report({"ERROR"}, "Unexpected file type (for "+game+", expected "+expectedExtension+")")
				return {"CANCELLED"}
		
		try:
			if game == "XC1":
				return import_brres(self, context)
			elif game == "XCX":
				self.report({"ERROR"}, "game not yet supported")
				return {"CANCELLED"}
			else:
				return import_sar1_skel_and_wimdo_and_wismt(self, context)
			self.report({"ERROR"}, "Unexpected error; code shouldn't be able to reach here")
			return {"CANCELLED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class MonadoForgeViewImportCleanupModelOperator(Operator):
	bl_idname = "object.monado_forge_cleanup_model_operator"
	bl_label = "Xenoblade Model Cleanup Operator"
	bl_description = "Does selected cleanup operations to all selected meshes"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context): # must have at least one mesh selected
		activeObject = context.view_layer.objects.active
		selectedObjects = context.view_layer.objects.selected
		if activeObject and activeObject.type == "MESH": return True
		for s in selectedObjects:
			if s.type == "MESH": return True
		return False
	
	def execute(self, context):
		try:
			objList = []
			activeObject = context.view_layer.objects.active
			selectedObjects = context.view_layer.objects.selected
			if activeObject and activeObject.type == "MESH":
				objList.append(activeObject)
			for s in selectedObjects:
				if s.type == "MESH" and s not in objList:
					objList.append(s)
			for obj in objList:
				cleanup_mesh(context,obj,context.scene.monado_forge_import.cleanupLooseVertices,
								context.scene.monado_forge_import.cleanupEmptyGroups,
								context.scene.monado_forge_import.cleanupEmptyColours,
								context.scene.monado_forge_import.cleanupEmptyOutlines,
								context.scene.monado_forge_import.cleanupEmptyShapes)
			return {"FINISHED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class MonadoForgeViewImportNodeLibraryOperator(Operator):
	bl_idname = "object.monado_forge_import_node_library_operator"
	bl_label = "Xenoblade Import Node From Library Operator"
	bl_description = "Creates a predetermined node group (and all prerequisites)"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			import_library_node(context.scene.monado_forge_import.nodePicker, self, context)
			return {"FINISHED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class MonadoForgeViewImportProperties(PropertyGroup):
	def defsPathSelectionCallback(self, context):
		# set the dataPath to match automatically, if one of the correct filetype exists
		defsFilename, defsFileExtension = os.path.splitext(self.defsPath)
		extMatching = {".camdo":".casmt",".wimdo":".wismt"}
		try:
			attemptedDataPath = defsFilename+extMatching[defsFileExtension]
		except KeyError:
			return
		if os.path.isfile(attemptedDataPath):
			self.dataPath = attemptedDataPath
	
	skeletonPath : StringProperty(
		name="Skeleton Path",
		description="File to import",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	boneSize : FloatProperty(
		name="Bone Size",
		description="Length of bones",
		default=0.1,
		min=0.01,
		soft_min=0.01,
		soft_max=10,
		unit="LENGTH",
	)
	importEndpoints : BoolProperty(
		name="Also Import Endpoints",
		description="Imports endpoints as well and adds them to the skeleton (in layer 2)",
		default=False,
	)
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
		update=defsPathSelectionCallback,
	)
	dataPath : StringProperty(
		name="Data Path",
		description="Data file to import",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	textureRepoMPath : StringProperty(
		name=r"\m\ Path",
		description=r"Path to \m\ texture repository",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	textureRepoHPath : StringProperty(
		name=r"\h\ Path",
		description=r"Path to \h\ texture repository",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	importToCursor : BoolProperty(
		name="Import To Cursor",
		description="Place the import at the 3D cursor (false: place it at [0,0,0])",
		default=False,
	)
	alsoImportLODs : BoolProperty(
		name="Also Import LODs",
		description="Include lower-detail meshes in the import",
		default=False,
	)
	mergeSharpEdges : BoolProperty(
		name="Merge Sharp Edges",
		description="Merge vertices even if their normals are different, relying only on custom normals and Sharp Edges",
		default=False,
	)
	doCleanupOnImport : BoolProperty(
		name="Clean Up After Import",
		description="Perform selected cleanup tasks once import is complete",
		default=True,
	)
	importUncachedTextures : BoolProperty(
		name="Import Uncached Textures",
		description="Uncheck to skip importing the large and slow textures",
		default=True,
	)
	autoSaveTextures : BoolProperty(
		name="Auto-Save Textures",
		description="Save extracted textures to disk",
		default=True,
	)
	texturePath : StringProperty(
		name="Texture Output Path",
		description="Folder where textures will be auto-saved to (WARNING: will overwrite existing!)",
		default="",
		maxlen=1024,
		subtype="FILE_PATH",
	)
	def duplicateImageMethodCallback(self, context):
		return (
			("ADD","Add","Import a new copy of the image (may result in more than expected due to multiple resolutions)"),
			("USE","Use","Skip import and simply re-use the existing image"),
			("REPLACE","Replace","Delete the existing image and have all its usages repointed to the new import"),
		)
	duplicateImageMethod : EnumProperty(
		name="Duplicate Image Method",
		items=duplicateImageMethodCallback,
		description="If an image of the same name already exists in this file",
		default=0,
	)
	skipMaterialImport : BoolProperty(
		name="Skip Material Import",
		description="Skips importing textures and materials entirely",
		default=False,
	)
	createDummyShader : BoolProperty(
		name="Create Dummy Shader",
		description="Run new materials through a simple base-colour-only Principled BSDF (false: use an empty group node instead)",
		default=True,
	)
	fixedViewportColour : BoolProperty(
		name="Set Viewport Colour",
		description="Set imported meshes to use a specific import colour (false: use material's base colour)",
		default=False,
	)
	viewportColour : FloatVectorProperty(
		name="Viewport Colour",
		description="Imported meshes have this viewport colour",
		default=[1.0,1.0,1.0,1.0],
		size=4,
		min=0.0,
		max=1.0,
		subtype="COLOR",
	)
	importOutlineData : BoolProperty(
		name="Import Outline Data",
		description="Import outline data and apply it as a vertex colour layer, a vertex weight group, and a solidify modifier (does not (yet) apply materials or clean up such extra models)",
		default=True,
	)
	maxOutlineThickness : FloatProperty(
		name="Max Thickness",
		description="Thickness of outline at maximum",
		default=0.002,
		min=0.0,
		soft_min=0.0,
		soft_max=0.1,
		unit="LENGTH",
	)
	minOutlineFactor : FloatProperty(
		name="Min Thickness",
		description="Thickness of outline at minimum",
		default=0.02,
		min=0.0,
		soft_min=0.0,
		soft_max=1.0,
		max=100.0,
		subtype="PERCENTAGE",
	)
	cleanupLooseVertices : BoolProperty(
		name="Loose Vertices",
		description="Erase vertices not connected to anything",
		default=True,
	)
	cleanupEmptyGroups : BoolProperty(
		name="Empty Groups",
		description="Erase vertex groups with nothing using them",
		default=True,
	)
	cleanupEmptyColours : BoolProperty(
		name="Empty Colours",
		description="Erase vertex colours that have no value (pure white or black with pure 1.0 or 0.0 alpha)",
		default=True,
	)
	cleanupEmptyOutlines : BoolProperty(
		name="Empty Outlines",
		description="Erase outline data if all vertices have 0 in the OutlineThickness group",
		default=True,
	)
	cleanupEmptyShapes : BoolProperty(
		name="Empty Shapes",
		description="Erase shape keys that have no effect",
		default=False,
	)
	differentiateTextures : BoolProperty(
		name="Differentiate Image Names",
		description="Appends the filename to the start of texture names (so they don't overwrite existing ones)",
		default=True,
	)
	differentiateTempTextures : BoolProperty(
		name="Differentiate Temp Images",
		description="Appends the filename to the start of temp texture names (regardless of the more general setting)",
		default=True,
	)
	blueBC5 : BoolProperty(
		name="Normalize BC5s",
		description="Assume that BC5-format images are normal maps, and calculate the blue channel accordingly",
		default=True,
	)
	splitTemps : BoolProperty(
		name="Dechannelise \"temp\" Files",
		description="If the image is named \"temp0000\" or similar, splits it out into an independent file per channel",
		default=True,
	)
	keepAllResolutions : BoolProperty(
		name="Keep All Resolutions",
		description="Include all textures, even if there's a larger resolution of the same",
		default=False,
	)
	compressEDVs : BoolProperty(
		name="Compress EDV nodes",
		description="Make extra data values take up less space in the material node setup",
		default=False,
	)
	def nodeLibraryCallback(self, context):
		nodeList = [
			("BasicMetallic","Basic Metallic Shader","(S) Metallic-style PBR shader with inputs tailored for the average Xenoblade model"),
			("BasicSpecular","Basic Specular Shader","(S) Specular-style shader with inputs tailored for the average Xenoblade model"),
			("CombineNormals","Combine Normals","(S) Combines two normal maps using reoriented normal mapping"),
			("FurShells","Fur Shells","(G) Expands a mesh outwards to simulate fur"),
			("TBNMatrix","TBN Matrix","(S) Outputs tangent-bitangent-normal triplet, given normal map and mesh tangent"),
			("TexInset","Texture Inset","(S) Distorts UVs for an inset (parallax) effect, given UVs, mesh tangent, normal map, and depth"),
			("UVPreProcess","UV Pre-Process","(S) Clamps and/or mirrors UVs outside bounds"),
		]
		if bpy.app.version < (4,0,0):
			del(nodeList[3]) # repeat zone not supported, can't do fur shell
		return nodeList
	nodePicker : EnumProperty(
		name="Node",
		items=nodeLibraryCallback,
		description="Node to add",
		default=0,
	)

class OBJECT_PT_MonadoForgeViewImportPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportPanel"
	bl_label = "Import"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgePanel"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		activeObject = bpy.context.view_layer.objects.active
		expectedSkeletonExtension = {"XC1":".brres","XCX":".xcx","XC2":".arc","XC1DE":".chr","XC3":".chr",}[scn.monado_forge_main.game]
		if scn.monado_forge_main.game == "XC1":
			col.prop(scn.monado_forge_import, "singlePath", text=".brres")
		else:
			col.prop(scn.monado_forge_import, "skeletonPath", text=expectedSkeletonExtension)
			col.prop(scn.monado_forge_import, "defsPath", text=".wimdo")
			col.prop(scn.monado_forge_import, "dataPath", text=".wismt")
		col.prop(scn.monado_forge_import, "importUncachedTextures")
		if scn.monado_forge_main.game == "XC3":
			texMHGroup = col.column(align=True)
			texMHGroup.prop(scn.monado_forge_import, "textureRepoMPath", text="\\m\\")
			texMHGroup.prop(scn.monado_forge_import, "textureRepoHPath", text="\\h\\")
			texMHGroup.enabled = scn.monado_forge_import.importUncachedTextures
		col.prop(scn.monado_forge_import, "autoSaveTextures")
		texturePathRow = col.row()
		texturePathRow.prop(scn.monado_forge_import, "texturePath", text="...to")
		texturePathRow.enabled = scn.monado_forge_import.autoSaveTextures
		col.prop(scn.monado_forge_import, "duplicateImageMethod", text="Duping")
		col.separator()
		if scn.monado_forge_main.game == "XC1":
			col.operator(MonadoForgeViewImportModelWithSkeletonOperator.bl_idname, text="Import BRRES", icon="IMPORT")
		else:
			col.operator(MonadoForgeViewImportSkeletonOperator.bl_idname, text="Import Skeleton Only", icon="IMPORT")
			col.operator(MonadoForgeViewImportModelOperator.bl_idname, text="Import Model Only", icon="IMPORT")
			col.operator(MonadoForgeViewImportModelWithSkeletonOperator.bl_idname, text="Import Model With Skeleton", icon="IMPORT")

class OBJECT_PT_MonadoForgeViewImportSkeletonOptionsPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportSkeletonOptionsPanel"
	bl_label = "Skeleton Import Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_import, "boneSize")
		if scn.monado_forge_main.game != "XC1": # BRRES endpoints are just normal bones, conceptually always selected/indistinguishable
			col.prop(scn.monado_forge_import, "importEndpoints")

class OBJECT_PT_MonadoForgeViewImportModelOptionsPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportModelOptionsPanel"
	bl_label = "Model Import Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_import, "importToCursor")
		if scn.monado_forge_main.game != "XC1":
			col.prop(scn.monado_forge_import, "alsoImportLODs")
		if scn.monado_forge_main.game != "XC1" and scn.monado_forge_main.game != "XCX":
			col.prop(scn.monado_forge_import, "importOutlineData")
		col.prop(scn.monado_forge_import, "mergeSharpEdges")
		col.prop(scn.monado_forge_import, "doCleanupOnImport")
		col.operator(MonadoForgeViewImportCleanupModelOperator.bl_idname, text="Clean Up Selected Meshes", icon="BRUSH_DATA")

class OBJECT_PT_MonadoForgeViewImportTextureOptionsPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportTextureOptionsPanel"
	bl_label = "Texture Import Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_import, "differentiateTextures")
		if scn.monado_forge_main.game != "XC1":
			col.prop(scn.monado_forge_import, "differentiateTempTextures")
			col.prop(scn.monado_forge_import, "blueBC5")
			col.prop(scn.monado_forge_import, "splitTemps")
			col.prop(scn.monado_forge_import, "keepAllResolutions")

class OBJECT_PT_MonadoForgeViewImportMaterialOptionsPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportMaterialOptionsPanel"
	bl_label = "Material Import Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_import, "skipMaterialImport")
		col.prop(scn.monado_forge_import, "createDummyShader")
		col.prop(scn.monado_forge_import, "fixedViewportColour")
		if scn.monado_forge_import.fixedViewportColour:
			col.prop(scn.monado_forge_import, "viewportColour", text="")
		col.prop(scn.monado_forge_import, "compressEDVs")

class OBJECT_PT_MonadoForgeViewImportOutlinePanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportOutlinePanel"
	bl_label = "Model Outline Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportModelOptionsPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		if scn.monado_forge_main.game == "XC1" or scn.monado_forge_main.game == "XCX":
			col.label(text="(no options)")
		else:
			layout.enabled = scn.monado_forge_import.importOutlineData
			col.prop(scn.monado_forge_import, "maxOutlineThickness")
			col.prop(scn.monado_forge_import, "minOutlineFactor")

class OBJECT_PT_MonadoForgeViewImportCleanupPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportCleanupPanel"
	bl_label = "Model Cleanup Options"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportModelOptionsPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_import, "cleanupLooseVertices")
		col.prop(scn.monado_forge_import, "cleanupEmptyGroups")
		col.prop(scn.monado_forge_import, "cleanupEmptyColours")
		col.prop(scn.monado_forge_import, "cleanupEmptyOutlines")
		col.prop(scn.monado_forge_import, "cleanupEmptyShapes")

class OBJECT_PT_MonadoForgeViewImportNodeLibraryPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewImportNodeLibraryPanel"
	bl_label = "Node Library"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgeViewImportPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_import, "nodePicker")
		col.operator(MonadoForgeViewImportNodeLibraryOperator.bl_idname, text="Add", icon="PLUS")

classes = (
			MonadoForgeViewImportSkeletonOperator,
			MonadoForgeViewImportModelOperator,
			MonadoForgeViewImportModelWithSkeletonOperator,
			MonadoForgeViewImportCleanupModelOperator,
			MonadoForgeViewImportNodeLibraryOperator,
			MonadoForgeViewImportProperties,
			OBJECT_PT_MonadoForgeViewImportPanel,
			OBJECT_PT_MonadoForgeViewImportSkeletonOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportModelOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportTextureOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportMaterialOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportOutlinePanel,
			OBJECT_PT_MonadoForgeViewImportCleanupPanel,
			OBJECT_PT_MonadoForgeViewImportNodeLibraryPanel,
			)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

	bpy.types.Scene.monado_forge_import = PointerProperty(type=MonadoForgeViewImportProperties)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.monado_forge_import

#[...]