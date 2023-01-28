import bpy
import math
import mathutils
import os
import traceback
from bpy.props import (
						BoolProperty,
						FloatProperty,
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
			printProgress = context.scene.monado_forge_main.printProgress
			absolutePath = bpy.path.abspath(context.scene.monado_forge_import.skeletonPath)
			boneSize = context.scene.monado_forge_import.boneSize
			positionEpsilon = context.scene.monado_forge_main.positionEpsilon
			angleEpsilon = context.scene.monado_forge_main.angleEpsilon
			importEndpoints = context.scene.monado_forge_import.importEndpoints
			if printProgress:
				print("Importing skeleton from: "+absolutePath)
			
			filename, fileExtension = os.path.splitext(absolutePath)
			expectedExtension = {"XC1":".brres","XCX":".xcx","XC2":".arc","XC1DE":".chr","XC3":".chr",}[game]
			if fileExtension != expectedExtension:
				self.report({"ERROR"}, "Unexpected file type (for "+game+", expected "+expectedExtension+")")
				return {"CANCELLED"}
			
			# first, read in the data and store it in a game-agnostic way
			if game == "XC1":
				modelFormat = "BRES"
				endian = "big"
			elif game == "XCX":
				modelFormat = "[xcx]"
				endian = "big"
			elif game == "XC2":
				modelFormat = "SAR1"
				endian = "little"
			elif game == "XC1DE":
				modelFormat = "SAR1"
				endian = "little"
			elif game == "XC3":
				modelFormat = "SAR1"
				endian = "little"
			
			importedSkeletons = []
			with open(absolutePath, "rb") as f:
				if modelFormat == "BRES":
					self.report({"ERROR"}, ".brres format not yet supported")
					return {"CANCELLED"}
				elif modelFormat == ".xcx":
					self.report({"ERROR"}, "(whatever XCX uses) format not yet supported")
					return {"CANCELLED"}
				elif modelFormat == "SAR1":
					magic = f.read(4)
					if magic != b"1RAS":
						self.report({"ERROR"}, "Not a valid "+expectedExtension+" file (unexpected header)")
						return {"CANCELLED"}
					fileSize = readAndParseInt(f,4,endian)
					version = readAndParseInt(f,4,endian)
					numFiles = readAndParseInt(f,4,endian)
					tocOffset = readAndParseInt(f,4,endian)
					dataOffset = readAndParseInt(f,4,endian)
					unknown1 = readAndParseInt(f,4,endian)
					unknown2 = readAndParseInt(f,4,endian)
					path = readStr(f)
					
					for i in range(numFiles):
						f.seek(tocOffset+i*0x40)
						offset = readAndParseInt(f,4,endian)
						size = readAndParseInt(f,4,endian)
						unknown = readAndParseInt(f,4,endian)
						filename = readStr(f)
						# todo: try to do this based on file type instead of name
						if game == "XC3":
							skelFilename = "skeleton"
						else: # XC2, XC1DE
							skelFilename = ".skl"
						if skelFilename not in filename: # yes, we're just dropping everything that's not a skeleton, this ain't a general-purpose script
							continue
						
						f.seek(offset)
						bcMagic = f.read(4)
						if bcMagic == b"LCHC": # some sort of special case I guess? (seen in XBC2ModelDecomp)
							continue
						if bcMagic != b"BC\x00\x00": # BC check
							self.report({"ERROR"}, "BC check failed for "+filename+" (dunno what this means tbh, file probably bad in some way e.g. wrong endianness)")
							continue
						blockCount = readAndParseInt(f,4,endian)
						fileSize = readAndParseInt(f,4,endian)
						pointerCount = readAndParseInt(f,4,endian)
						dataOffset = readAndParseInt(f,4,endian)
						
						f.seek(offset+dataOffset+4)
						skelMagic = f.read(4)
						if skelMagic != b"SKEL":
							self.report({"ERROR"}, ".skl file "+filename+" has bad header")
							return {"CANCELLED"}
						
						skelHeaderUnknown1 = readAndParseInt(f,4,endian)
						skelHeaderUnknown2 = readAndParseInt(f,4,endian)
						skelTocItems = []
						for j in range(10): # yeah it's a magic number, deal with it
							itemOffset = readAndParseInt(f,4,endian)
							itemUnknown1 = readAndParseInt(f,4,endian)
							itemCount = readAndParseInt(f,4,endian)
							itemUnknown2 = readAndParseInt(f,4,endian)
							skelTocItems.append([itemOffset,itemUnknown1,itemCount,itemUnknown2])
						
						# finally we have the datums
						# TOC layout:
						# [0]: ???
						# [1]: ???
						# [2]: bone parent IDs
						# [3]: bone names
						# [4]: bone data (posititon, rotation, scale)
						# [5]: ???
						# [6]: endpoint parent IDs
						# [7]: endpoint names
						# [8]: endpoint data (position, rotation, scale)
						# [9]: ???
						if (skelTocItems[2][2] != skelTocItems[3][2]) or (skelTocItems[3][2] != skelTocItems[4][2]):
							print("bone parent entries: "+str(skelTocItems[2][2]))
							print("bone name entries: "+str(skelTocItems[3][2]))
							print("bone data entries: "+str(skelTocItems[4][2]))
							self.report({"ERROR"}, ".skl file "+filename+" has inconsistent bone counts (see console)")
							return {"CANCELLED"}
						if importEndpoints:
							if (skelTocItems[6][2] != skelTocItems[7][2]) or (skelTocItems[7][2] != skelTocItems[8][2]):
								print("endpoint parent entries: "+str(skelTocItems[6][2]))
								print("endpoint name entries: "+str(skelTocItems[7][2]))
								print("endpoint data entries: "+str(skelTocItems[8][2]))
								self.report({"WARNING"}, ".skl file "+filename+" has inconsistent endpoint counts (see console); endpoint import skipped")
						forgeBones = []
						for b in range(skelTocItems[2][2]):
							# parent
							f.seek(offset+skelTocItems[2][0]+b*2)
							parent = readAndParseInt(f,2,endian)
							# name
							f.seek(offset+skelTocItems[3][0]+b*16)
							nameOffset = readAndParseInt(f,4,endian)
							f.seek(offset+nameOffset)
							name = readStr(f)
							# data
							f.seek(offset+skelTocItems[4][0]+b*(4*12))
							px = readAndParseFloat(f,endian)
							py = readAndParseFloat(f,endian)
							pz = readAndParseFloat(f,endian)
							pw = readAndParseFloat(f,endian)
							rx = readAndParseFloat(f,endian)
							ry = readAndParseFloat(f,endian)
							rz = readAndParseFloat(f,endian)
							rw = readAndParseFloat(f,endian)
							sx = readAndParseFloat(f,endian)
							sy = readAndParseFloat(f,endian)
							sz = readAndParseFloat(f,endian)
							sw = readAndParseFloat(f,endian)
							# reminder that the pos and scale are x,y,z,w but the rotation is w,x,y,z
							fb = MonadoForgeBone()
							fb.setParent(parent)
							fb.setName(name)
							fb.setPosition([px,py,pz,pw])
							fb.setRotation([rw,rx,ry,rz])
							fb.setScale([sx,sy,sz,sw])
							fb.setEndpoint(False)
							forgeBones.append(fb)
						if importEndpoints:
							for ep in range(skelTocItems[6][2]):
								# parent
								f.seek(offset+skelTocItems[6][0]+ep*2)
								parent = readAndParseInt(f,2,endian)
								# name
								f.seek(offset+skelTocItems[7][0]+ep*8) # yeah endpoint names are packed tighter than "normal" bone names
								nameOffset = readAndParseInt(f,4,endian)
								f.seek(offset+nameOffset)
								name = readStr(f)
								# data
								f.seek(offset+skelTocItems[8][0]+ep*(4*12))
								px = readAndParseFloat(f,endian)
								py = readAndParseFloat(f,endian)
								pz = readAndParseFloat(f,endian)
								pw = readAndParseFloat(f,endian)
								rx = readAndParseFloat(f,endian)
								ry = readAndParseFloat(f,endian)
								rz = readAndParseFloat(f,endian)
								rw = readAndParseFloat(f,endian)
								sx = readAndParseFloat(f,endian)
								sy = readAndParseFloat(f,endian)
								sz = readAndParseFloat(f,endian)
								sw = readAndParseFloat(f,endian)
								# for some reason, endpoints tend to have pw = 0, which positions it relative to root instead of parent (and we don't want that)
								if pw == 0.0: pw = 1.0
								# reminder that the pos and scale are x,y,z,w but the rotation is w,x,y,z
								fb = MonadoForgeBone()
								fb.setParent(parent)
								fb.setName(name)
								fb.setPosition([px,py,pz,pw])
								fb.setRotation([rw,rx,ry,rz])
								fb.setScale([sx,sy,sz,sw])
								fb.setEndpoint(True)
								forgeBones.append(fb)
						if printProgress:
							print("Read "+str(len(forgeBones))+" bones.")
						importedSkeletons.append(forgeBones)
					if not importedSkeletons:
						self.report({"ERROR"}, "No valid .skl items found in file")
						return {"CANCELLED"}
				else:
					self.report({"ERROR"}, "Unknown format: "+modelFormat)
					return {"CANCELLED"}
			
			# we now have the skeletons in generic format - create the armatures
			for skeleton in importedSkeletons:
				armatureName = skeleton[0].getName()
				if armatureName.endswith("_top"):
					armatureName = armatureName[:-4]
				if armatureName.endswith("_Bone"):
					armatureName = armatureName[:-5]
				create_armature_from_bones(skeleton,armatureName,boneSize,positionEpsilon,angleEpsilon)
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
		return context.scene.monado_forge_import.singlePath or context.scene.monado_forge_import.defsPath # or context.scene.monado_forge_import.dataPath
	
	def execute(self, context):
		game = context.scene.monado_forge_main.game
		# this isn't part of the poll because it's not a trivial check and the fix needs to be more descriptive
		if context.scene.monado_forge_import.autoSaveTextures:
			if not os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.texturePath)):
				self.report({"ERROR"}, "Auto-save selected, but texture output path is not an existing folder")
				return {"CANCELLED"}
		if game == "XC3" and not (os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.textureRepoMPath)) and os.path.isdir(bpy.path.abspath(context.scene.monado_forge_import.textureRepoHPath))):
			self.report({"ERROR"}, "Import uncached textures selected, but no texture repositories provided (both are required)")
			return {"CANCELLED"}
		try:
			if game == "XC1" or game == "XCX":
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
	#bl_description = "Imports a model and skeleton from a Xenoblade file"
	bl_description = "to be continued.."
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		return False
	
	def execute(self, context):
		pass

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
				if s.type == "MESH":
					objList.append(s)
			for obj in objList:
				cleanup_mesh(context,obj,context.scene.monado_forge_import.cleanupLooseVertices,context.scene.monado_forge_import.cleanupEmptyGroups,context.scene.monado_forge_import.cleanupEmptyShapes)
			return {"FINISHED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class MonadoForgeViewImportProperties(PropertyGroup):
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
	tempWeightTableOverride : IntProperty(
		name="Weight Table Override",
		description="Force all meshes to use this weight table (see readme for explanation)",
		default=0,
		min=0,
	)
	alsoImportLODs : BoolProperty(
		name="Also Import LODs",
		description="Include lower-detail meshes in the import",
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
	blueBC5 : BoolProperty(
		name="Normalize BC5s",
		description="Assume that BC5-format images are normal maps, and calculate the blue channel accordingly",
		default=True,
	)
	splitTemps : BoolProperty(
		name="Dechannelise \"temp\" Files",
		description="(warning: slow, thinking of a better way to implement the feature)\nIf the image is named \"temp0000\" or similar, splits it out into an independent file per channel",
		default=False,
	)
	keepAllResolutions : BoolProperty(
		name="Keep All Resolutions",
		description="Include all textures, even if there's a larger resolution of the same",
		default=False,
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
		col.prop(scn.monado_forge_import, "skeletonPath", text=expectedSkeletonExtension)
		if scn.monado_forge_main.game == "XC1":
			col.prop(scn.monado_forge_import, "singlePath", text=".brres")
		else:
			defsRow = col.row()
			defsRow.prop(scn.monado_forge_import, "defsPath", text=".wimdo")
			dataRow = col.row()
			dataRow.prop(scn.monado_forge_import, "dataPath", text=".wismt")
		col.prop(scn.monado_forge_import, "importUncachedTextures")
		if scn.monado_forge_main.game == "XC3":
			texMRow = col.row()
			texMRow.prop(scn.monado_forge_import, "textureRepoMPath", text="\\m\\")
			texMRow.enabled = scn.monado_forge_import.importUncachedTextures
			texHRow = col.row()
			texHRow.prop(scn.monado_forge_import, "textureRepoHPath", text="\\h\\")
			texHRow.enabled = scn.monado_forge_import.importUncachedTextures
		col.prop(scn.monado_forge_import, "autoSaveTextures")
		texturePathRow = col.row()
		texturePathRow.prop(scn.monado_forge_import, "texturePath", text="...to")
		texturePathRow.enabled = scn.monado_forge_import.autoSaveTextures
		col.separator()
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
		epSubcol = col.column()
		epSubcol.prop(scn.monado_forge_import, "importEndpoints")
		if scn.monado_forge_main.game == "XC1": # endpoints are just normal bones, conceptually always selected
			epSubcol.enabled = False

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
		col.prop(scn.monado_forge_import, "tempWeightTableOverride")
		col.prop(scn.monado_forge_import, "alsoImportLODs")
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
		col.prop(scn.monado_forge_import, "blueBC5")
		col.prop(scn.monado_forge_import, "splitTemps")
		col.prop(scn.monado_forge_import, "keepAllResolutions")

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
		col.prop(scn.monado_forge_import, "cleanupEmptyShapes")

classes = (
			MonadoForgeViewImportSkeletonOperator,
			MonadoForgeViewImportModelOperator,
			MonadoForgeViewImportModelWithSkeletonOperator,
			MonadoForgeViewImportCleanupModelOperator,
			MonadoForgeViewImportProperties,
			OBJECT_PT_MonadoForgeViewImportPanel,
			OBJECT_PT_MonadoForgeViewImportSkeletonOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportModelOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportTextureOptionsPanel,
			OBJECT_PT_MonadoForgeViewImportCleanupPanel,
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