import bpy
import math
import mathutils
import os
import struct
import traceback
from bpy.props import (
						BoolProperty,
						EnumProperty,
						FloatProperty,
						PointerProperty,
						StringProperty,
						)
from bpy.types import (
						AddonPreferences,
						Operator,
						Panel,
						PropertyGroup,
						)

bl_info = {
	"name": "Xenoblade Skeleton Tools",
	"description": "Manipulate skeletons from Xenoblade games",
	"author": "Sir Teatei Moonlight (xenoserieswiki.org/tools)",
	"version": (0, 7, 1),
	"blender": (3, 3, 1),
	"category": "Armature",
}

u8CodeB = ">B"
i8CodeB = ">b"
u16CodeB = ">H"
i16CodeB = ">h"
u32CodeB = ">L"
i32CodeB = ">l"
fpCodeB = ">f"
u8CodeL = "<B"
i8CodeL = "<b"
u16CodeL = "<H"
i16CodeL = "<h"
u32CodeL = "<L"
i32CodeL = "<l"
fpCodeL = "<f"

# old games are big and new ones are little, so assume little as default
def readAndParseInt(inFile,bytes,signed=False,endian="little"):
	if endian == "big":
		return readAndParseIntBig(infile,bytes,signed)
	if bytes == 1:
		parseString = i8CodeL if signed else u8CodeL
	elif bytes == 2:
		parseString = i16CodeL if signed else u16CodeL
	elif bytes == 4:
		parseString = i32CodeL if signed else u32CodeL
	else:
		raise ValueException("invalid int bytesize: "+str(bytes))
	return struct.unpack(parseString,inFile.read(struct.calcsize(parseString)))[0]
def readAndParseIntBig(inFile,bytes,signed=False):
	if bytes == 1:
		parseString = i8CodeB if signed else u8CodeB
	elif bytes == 2:
		parseString = i16CodeB if signed else u16CodeB
	elif bytes == 4:
		parseString = i32CodeB if signed else u32CodeB
	else:
		raise ValueException("invalid int bytesize: "+str(bytes))
	return struct.unpack(parseString,inFile.read(struct.calcsize(parseString)))[0]

def readAndParseFloat(inFile,endian="little"):
	if endian == "big":
		return readAndParseFloatBig(infile)
	return struct.unpack(fpCodeL,inFile.read(struct.calcsize(fpCodeL)))[0]
def readAndParseFloatBig(inFile):
	return struct.unpack(fpCodeB,inFile.read(struct.calcsize(fpCodeB)))[0]

def readStr(inFile):
	strBytes = b""
	c = inFile.read(1)
	while c != b"\x00" and c != b"":
		strBytes += c
		c = inFile.read(1)
	return strBytes.decode("utf-8")
def readFixedLenStr(inFile,length):
	strBytes = b""
	for i in range(length):
		c = inFile.read(1)
		strBytes += c
	return strBytes.decode("utf-8")

rad90 = math.radians(90)
rad180 = math.radians(180)
rad360 = math.radians(360)
rad720 = math.radians(720)

def flipRoll(roll):
	return roll % rad360 - rad180

def clampBoneRoll(editBone,angleEpsilon):
	# limits roll to being between -180 and +180
	roll = editBone.roll
	while roll > rad180: roll -= rad180
	while roll < -rad180: roll += rad180
	if abs(roll) < angleEpsilon:
		roll = 0
	editBone.roll = roll

def mirrorBone(editBone,otherBone):
	# replaces editBone's position and rotation with a mirrored version of otherBone's
	roll = editBone.roll
	editBone.matrix = otherBone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
	editBone.head = otherBone.head * mathutils.Vector((-1,1,1))
	editBone.tail = otherBone.tail * mathutils.Vector((-1,1,1))
	editBone.roll = -otherBone.roll

def isBonePairAutoMirrorable(thisBone,otherBone,positionEpsilon,angleEpsilon):
	# the logic: would the mirrored bone equal the target bone within epsilon? if so, mirror, else do not
	# the metrics are head position, angle between Y-axes (facing direction), and angle between Z-axes (roll)
	pos1 = thisBone.head
	pos2 = otherBone.head
	pos1 = pos1 * mathutils.Vector((-1,1,1))
	for p in range(3):
		posDiff = abs(pos1[p] - pos2[p])
		if posDiff >= positionEpsilon:
			return False,"position["+str(p)+"] diff. of "+str(posDiff)+" (out of tolerance by "+str(positionEpsilon-posDiff)+")"
	vector1 = thisBone.y_axis
	vector2 = otherBone.y_axis
	vector1 = vector1 @ mathutils.Matrix([[-1,0,0],[0,1,0],[0,0,1]])
	angleDiff = vector1.angle(vector2)
	if angleDiff > rad90: angleDiff = abs(rad180 - angleDiff) # both "0 degrees apart" and "180 degrees apart" are correct for mirroring
	if (angleDiff >= angleEpsilon):
		return False,"facing vector angle diff. of "+str(math.degrees(angleDiff))+"d (out of tolerance by "+str(math.degrees(angleEpsilon-angleDiff))+"d)"
	vector1 = thisBone.z_axis
	vector2 = otherBone.z_axis
	vector1 = vector1 @ mathutils.Matrix([[-1,0,0],[0,1,0],[0,0,1]])
	angleDiff = vector1.angle(vector2)
	if angleDiff > rad90: angleDiff = abs(rad180 - angleDiff) # same as above
	if (angleDiff >= angleEpsilon):
		return False,"roll angle diff. of "+str(math.degrees(angleDiff))+"d (out of tolerance by "+str(math.degrees(angleEpsilon-angleDiff))+"d)"
	return True,""

class XBSkeletonImportOperator(Operator):
	bl_idname = "object.xb_skeleton_import_operator"
	bl_label = "Xenoblade Skeleton Import Operator"
	bl_description = "Imports a skeleton from a Xenoblade file"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			game = context.scene.xb_skeleton_import.game
			absolutePath = bpy.path.abspath(context.scene.xb_skeleton_import.path)
			boneSize = context.scene.xb_skeleton_import.boneSize
			positionEpsilon = context.scene.xb_skeleton_import.positionEpsilon
			angleEpsilon = context.scene.xb_skeleton_import.angleEpsilon
			importEndpoints = context.scene.xb_skeleton_import.importEndpoints
			print("Importing skeleton from: "+absolutePath)
			
			filename, fileExtension = os.path.splitext(absolutePath)
			expectedExtension = {"XC1":".brres","XCX":".xcx","XC2":".arc","XC1DE":".chr","XC3":".chr",}[game]
			if fileExtension != expectedExtension:
				self.report({"ERROR"}, "Unexpected file type (for "+game+", expected "+expectedExtension+")")
				return {"CANCELLED"}
			
			# first, read in the data and store it in a game-agnostic way
			# [name, parent, [px,py,pz,pw], [rw,rx,ry,rz], [sx,sy,sz,sw], isEndpoint]
			# note how the rotation's w comes first, that's how Blender needs it
			
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
						self.report({"ERROR"}, "Not a valid .chr file (unexpected header)")
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
						if ".skl" not in filename: # yes, we're just dropping everything that's not a skeleton, this ain't a general-purpose script
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
						for j in range(9): # a magic number from XBC2ModelDecomp
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
						boneParentIDs = []
						boneNames = []
						boneData = []
						boneIsEndpoint = []
						for b in range(skelTocItems[2][2]):
							# parent
							f.seek(offset+skelTocItems[2][0]+b*2)
							parent = readAndParseInt(f,2,endian)
							boneParentIDs.append(parent)
							# name
							f.seek(offset+skelTocItems[3][0]+b*16)
							nameOffset = readAndParseInt(f,4,endian)
							f.seek(offset+nameOffset)
							name = readStr(f)
							boneNames.append(name)
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
							boneData.append([[px,py,pz,pw],[rw,rx,ry,rz],[sx,sy,sz,sw]])
							boneIsEndpoint.append(False)
						if importEndpoints:
							for ep in range(skelTocItems[6][2]):
								# parent
								f.seek(offset+skelTocItems[6][0]+ep*2)
								parent = readAndParseInt(f,2,endian)
								boneParentIDs.append(parent)
								# name
								f.seek(offset+skelTocItems[7][0]+ep*8) # yeah they're packed tighter than the bone names
								nameOffset = readAndParseInt(f,4,endian)
								f.seek(offset+nameOffset)
								name = readStr(f)
								boneNames.append(name)
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
								# for some reason, endpoints tend to have pw = 0, which positions it based on root (and we don't want that)
								if pw == 0.0: pw = 1.0
								# reminder that the pos and scale are x,y,z,w but the rotation is w,x,y,z
								boneData.append([[px,py,pz,pw],[rw,rx,ry,rz],[sx,sy,sz,sw]])
								boneIsEndpoint.append(True)
						# transform the split lists into a single one
						boneList = []
						for b in range(len(boneParentIDs)):
							boneList.append([boneParentIDs[b],boneNames[b],boneData[b][0],boneData[b][1],boneData[b][2],boneIsEndpoint[b]])
						importedSkeletons.append(boneList)
					if not importedSkeletons:
						self.report({"ERROR"}, "No valid .skl items found in file")
						return {"CANCELLED"}
				else:
					self.report({"ERROR"}, "Unknown format: "+modelFormat)
					return {"CANCELLED"}
			
			# we now have the skeletons in generic format - create the armatures
			for s in importedSkeletons:
				bpy.ops.object.select_all(action="DESELECT")
				bpy.ops.object.armature_add(enter_editmode=True, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
				skeleton = bpy.context.view_layer.objects.active.data
				skeleton.show_names = True
				# delete the default bone to start with
				bpy.ops.armature.select_all(action="SELECT")
				bpy.ops.armature.delete()
				# start adding
				editBones = skeleton.edit_bones
				for b in s:
					# assumption: no bone will ever precede its parent (i.e. the parent will always be there already to attach to, no second pass needed)
					boneParent,boneName,bonePos,boneRot,boneScl,boneIsEndpoint = b[0],b[1],b[2],b[3],b[4],b[5]
					newBone = editBones.new(boneName)
					newBone.length = boneSize
					newBone.parent = editBones[boneParent] if boneParent != 0xffff else None
					parentMatrix = newBone.parent.matrix if newBone.parent else mathutils.Matrix.Identity(4)
					posMatrix = mathutils.Matrix.Translation(bonePos)
					rotMatrix = mathutils.Quaternion(boneRot).to_matrix()
					rotMatrix.resize_4x4()
					newBone.matrix = parentMatrix @ (posMatrix @ rotMatrix)
					newBone.length = boneSize # have seen odd non-rounding when not doing this
					# put "normal" bones in layer 1 and endpoints in layer 2
					# must be done in this order or the [0] set will be dropped because bones must be in at least one layer
					newBone.layers[1] = boneIsEndpoint
					newBone.layers[0] = not boneIsEndpoint
				# now that the bones are in, spin them around so they point in a more logical-for-Blender direction
				for b in editBones:
					b.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix()) # transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
					roll = b.y_axis # roll gets lost after the following matrix mult for some reason, so preserve it
					b.matrix = b.matrix @ mathutils.Matrix([[0,1,0,0],[1,0,0,0],[0,0,1,0],[0,0,0,1]]) # change from +X being the "main axis" to +Y
					b.align_roll(roll)
					# everything done, now apply epsilons
					b.head = [(0 if abs(p) < positionEpsilon else p) for p in b.head]
					b.tail = [(0 if abs(p) < positionEpsilon else p) for p in b.tail]
					clampBoneRoll(b,angleEpsilon)
				# cleanup
				bpy.context.view_layer.objects.active.name = editBones[0].name
				bpy.ops.armature.select_all(action="DESELECT")
				bpy.ops.object.mode_set(mode="OBJECT")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class XBSkeletonBoneFlipAllOperator(Operator):
	bl_idname = "object.xb_skeleton_boneflip_all_operator"
	bl_label = "Xenoblade Skeleton Bone Flip All Operator"
	bl_description = "Flips all _R bones, pointing them the other way (reversible)"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			nonFinalMirror = context.scene.xb_skeleton_import.nonFinalMirror
			angleEpsilon = context.scene.xb_skeleton_import.angleEpsilon
			skeleton = bpy.context.view_layer.objects.active.data
			bpy.ops.object.mode_set(mode="EDIT")
			editBones = skeleton.edit_bones
			flipCount = 0
			for bone in editBones:
				if bone.name.endswith("_R") or (nonFinalMirror and "_R_" in bone.name):
					roll = bone.roll
					bone.matrix = bone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]])
					bone.roll = flipRoll(roll)
					clampBoneRoll(bone,angleEpsilon)
					flipCount += 1
			bpy.ops.object.mode_set(mode="OBJECT")
			self.report({"INFO"}, "Flipped "+str(flipCount)+" bones.")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class XBSkeletonBoneFlipSelectedOperator(Operator):
	bl_idname = "object.xb_skeleton_boneflip_selected_operator"
	bl_label = "Xenoblade Skeleton Bone Flip Selected Operator"
	bl_description = "Flips all selected bones, pointing them the other way (reversible)"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			angleEpsilon = context.scene.xb_skeleton_import.angleEpsilon
			# edit mode is assumed (panel is edit mode limited)
			for bone in bpy.context.selected_bones:
				roll = bone.roll
				bone.matrix = bone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]])
				bone.roll = flipRoll(roll)
				clampBoneRoll(bone,angleEpsilon)
			self.report({"INFO"}, "Flipped "+str(len(bpy.context.selected_bones))+" bones.")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class XBSkeletonBoneMirrorAutoOperator(Operator):
	bl_idname = "object.xb_skeleton_bonemirror_auto_operator"
	bl_label = "Xenoblade Skeleton Bone Mirror Auto Operator"
	bl_description = "Edits all _R bones to mirror the _L bones of the same name (destructive)"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			nonFinalMirror = context.scene.xb_skeleton_import.nonFinalMirror
			positionEpsilon = context.scene.xb_skeleton_import.positionEpsilon
			angleEpsilon = context.scene.xb_skeleton_import.angleEpsilon
			skeleton = bpy.context.view_layer.objects.active.data
			bpy.ops.object.mode_set(mode="EDIT")
			editBones = skeleton.edit_bones
			mirroredCount = 0
			outOfRangeCount = 0
			for bone in editBones:
				if bone.name.endswith("_R") or (nonFinalMirror and "_R_" in bone.name):
					mirrorName = ""
					otherBone = None
					if "_R" in bone.name: mirrorName = bone.name.replace("_R","_L")
					if "_L" in bone.name: mirrorName = bone.name.replace("_L","_R")
					try:
						otherBone = editBones[mirrorName]
					except KeyError:
						otherBone = None
					if otherBone:
						canAutoMirror,message = isBonePairAutoMirrorable(bone,otherBone,positionEpsilon,angleEpsilon)
						if canAutoMirror:
							mirrorBone(bone,otherBone)
							mirroredCount += 1
						else:
							print(bone.name+" != "+otherBone.name+" ~ "+message)
							outOfRangeCount += 1
			bpy.ops.object.mode_set(mode="OBJECT")
			if outOfRangeCount > 0:
				self.report({"WARNING"}, "Mirrored "+str(mirroredCount)+" bones but skipped "+str(outOfRangeCount)+" for being out of epsilon tolerance. See console for list.")
			else:
				self.report({"INFO"}, "Mirrored "+str(mirroredCount)+" bones.")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class XBSkeletonBoneMirrorSelectedOperator(Operator):
	bl_idname = "object.xb_skeleton_bonemirror_selected_operator"
	bl_label = "Xenoblade Skeleton Bone Mirror Selected Operator"
	bl_description = "Edits all selected bones to mirror the bones of the same name with reverse L/R polarity (destructive)"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			positionEpsilon = context.scene.xb_skeleton_import.positionEpsilon
			angleEpsilon = context.scene.xb_skeleton_import.angleEpsilon
			# edit mode is assumed (panel is edit mode limited)
			skeleton = bpy.context.view_layer.objects.active.data
			editBones = skeleton.edit_bones
			mirroredCount = 0
			outOfRangeCount = 0
			for bone in bpy.context.selected_bones:
				mirrorName = ""
				otherBone = None
				if "_R" in bone.name: mirrorName = bone.name.replace("_R","_L")
				if "_L" in bone.name: mirrorName = bone.name.replace("_L","_R")
				try:
					otherBone = editBones[mirrorName]
				except KeyError:
					otherBone = None
				if otherBone:
					canAutoMirror,message = isBonePairAutoMirrorable(bone,otherBone,positionEpsilon,angleEpsilon)
					if not canAutoMirror:
						print(bone.name+" != "+otherBone.name+" ~ "+message)
						outOfRangeCount += 1
					# but since the user selected this bone on purpose, we mirror it anyway
					mirrorBone(bone,otherBone)
					mirroredCount += 1
			if mirroredCount < len(bpy.context.selected_bones):
				self.report({"WARNING"}, "Did not mirror "+str(len(bpy.context.selected_bones)-mirroredCount)+" bones (no matching name on the other side).")
			if outOfRangeCount > 0:
				self.report({"WARNING"}, str(outOfRangeCount)+" bones were out of epsilon tolerance, but were mirrored anyway. See console for list.")
			else:
				self.report({"INFO"}, "Mirrored "+str(mirroredCount)+" bones.")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class XBSkeletonNonFinalLRFixOperator(Operator):
	bl_idname = "object.xb_skeleton_nonfinallrfix_operator"
	bl_label = "Xenoblade Skeleton Non Final LR Fix Operator"
	bl_description = "Edits bone names to put the _L/_R at the end"
	bl_options = {"REGISTER","UNDO"}
	
	def execute(self, context):
		try:
			skeleton = bpy.context.view_layer.objects.active.data
			bpy.ops.object.mode_set(mode="EDIT")
			editBones = skeleton.edit_bones
			count = 0
			for bone in editBones:
				# assumption: no bone can have both _L_ and _R_
				if "_L_" in bone.name:
					bone.name = bone.name.replace("_L_","_") + "_L"
					count += 1
				if "_R_" in bone.name:
					bone.name = bone.name.replace("_R_","_") + "_R"
					count += 1
			bpy.ops.object.mode_set(mode="OBJECT")
			self.report({"INFO"}, "Renamed "+str(count)+" bones.")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class XBSkeletonToolsProperties(PropertyGroup):

	def gameListCallback(self, context):
		return (
			#("XC1","XC1","Xenoblade 1 (Wii)"),
			#("XCX","XCX","Xenoblade X"),
			("XC2","XC2","Xenoblade 2"),
			("XC1DE","XC1DE","Xenoblade 1 DE"),
			("XC3","XC3","Xenoblade 3 (untested)"),
		)
	
	game : EnumProperty(
		name="Game",
		items=gameListCallback,
		description="Game to deal with",
		default=1, #"XC1DE"
	)
	path : StringProperty(
		name="Path",
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
	positionEpsilon : FloatProperty(
		name="Position Epsilon",
		description="Positions less than this are set to zero; positions within this are considered equal for auto-mirroring",
		default=0.0001, # 1 micrometer
		min=0,
		max=0.001, # 1 milimeter - we're working on human scales, 1mm is significant no matter what
		soft_min=0,
		soft_max=0.001,
		unit="LENGTH",
	)
	angleEpsilon : FloatProperty(
		name="Angle Epsilon",
		description="Angles less than this are set to zero; angles within this are considered equal for auto-mirroring",
		default=math.radians(0.1),
		min=0,
		max=math.radians(1), # 1 degree is significant no matter how you look at it
		soft_min=0,
		soft_max=1,
		step=1,
		unit="ROTATION",
	)
	nonFinalMirror : BoolProperty(
		name="Accept Non-Final L/R",
		description="Treat non-final _L_ and _R_ in bone names as being mirrored",
		default=True,
	)
	importEndpoints : BoolProperty(
		name="Also Import Endpoints",
		description="Imports endpoints as well and adds them to the skeleton (in layer 2)",
		default=False,
	)

class OBJECT_PT_XBSkeletonToolsPanel(Panel):
	bl_idname = "OBJECT_PT_XBSkeletonToolsPanel"
	bl_label = "Xenoblade Skeleton Tools"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Xenoblade"
	bl_context = "objectmode"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.label(text="General")
		col.prop(scn.xb_skeleton_import, "nonFinalMirror")
		col.prop(scn.xb_skeleton_import, "positionEpsilon")
		col.prop(scn.xb_skeleton_import, "angleEpsilon")
		col.separator(factor=2)
		col.label(text="Import")
		col.prop(scn.xb_skeleton_import, "game")
		col.prop(scn.xb_skeleton_import, "path", text="")
		col.prop(scn.xb_skeleton_import, "boneSize")
		col.prop(scn.xb_skeleton_import, "importEndpoints")
		col.separator()
		col.operator(XBSkeletonImportOperator.bl_idname, text="Import Skeleton", icon="IMPORT")
		col.separator(factor=2)
		col.label(text="Modify")
		col.operator(XBSkeletonBoneFlipAllOperator.bl_idname, text="Flip _R Bones", icon="ARROW_LEFTRIGHT")
		col.operator(XBSkeletonBoneMirrorAutoOperator.bl_idname, text="Mirror _R Bones", icon="MOD_MIRROR")
		col.operator(XBSkeletonNonFinalLRFixOperator.bl_idname, text="Fix Non-Final L/R Bone Names")

class ARMATURE_EDIT_PT_XBSkeletonToolsPanel(Panel):
	bl_idname = "ARMATURE_EDIT_PT_XBSkeletonToolsPanel"
	bl_label = "Xenoblade Skeleton Tools"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Xenoblade"
	bl_context = "armature_edit"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.operator(XBSkeletonBoneFlipSelectedOperator.bl_idname, text="Flip Selected Bones", icon="ARROW_LEFTRIGHT")
		col.operator(XBSkeletonBoneMirrorSelectedOperator.bl_idname, text="Mirror Selected Bones", icon="MOD_MIRROR")

classes = (
	XBSkeletonToolsProperties,
	OBJECT_PT_XBSkeletonToolsPanel,
	ARMATURE_EDIT_PT_XBSkeletonToolsPanel,
	XBSkeletonImportOperator,
	XBSkeletonBoneFlipAllOperator,
	XBSkeletonBoneFlipSelectedOperator,
	XBSkeletonBoneMirrorAutoOperator,
	XBSkeletonBoneMirrorSelectedOperator,
	XBSkeletonNonFinalLRFixOperator,
)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

	bpy.types.Scene.xb_skeleton_import = PointerProperty(type=XBSkeletonToolsProperties)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.xb_skeleton_import

if __name__ == "__main__":
	register()

#[...]