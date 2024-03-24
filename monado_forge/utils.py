import bpy
import io
import math
import mathutils
import numpy
import os
import struct
from contextlib import redirect_stdout

from . classes import *

# math constants

rad90 = math.radians(90)
rad180 = math.radians(180)
rad360 = math.radians(360)
rad720 = math.radians(720)

# useful stuff

def get_bit_from_right(x,b):
	return x & (1 << b)
def clamp(value,low,high):
	return max(low,min(value,high))
# ceiling division (as opposed to "//" floor division)
# https://stackoverflow.com/questions/14822184/
def ceildiv(a,b):
	return -(a // -b)
# https://stackoverflow.com/questions/12681945/
def reverse_int(n,l):
	result = 0
	for i in range(l):
		result = (result << 1) + (n & 1)
		n >>= 1
	return result
# https://stackabuse.com/python-how-to-flatten-list-of-lists/
def flattened_list(given_list):
	return [item for sublist in given_list for item in sublist]
def flattened_list_recursive(given_list):
	if len(given_list) == 0:
		return given_list
	if isinstance(given_list[0], list):
		return flattened_list_recursive(given_list[0]) + flattened_list_recursive(given_list[1:])
	return given_list[:1] + flattened_list_recursive(given_list[1:])
def print_colour(s,c):
	print(c+s+"\033[0m")
def print_error(s):
	print_colour(s,"\033[91m")
def print_warning(s):
	print_colour(s,"\033[93m")
def print_bar(p): # 0.0-1.0
	barLength = 25
	barsFilled = int(barLength*p)
	barsUnfilled = barLength-barsFilled
	print("["+"#"*barsFilled+"-"*barsUnfilled+"]",end="")
def print_progress_bar(n,d,t): # numerator, denominator, text
	if n == 0:
		print(t+": ",end="")
		print_bar(0)
		print(" 0 / "+str(d)+" ")
	elif n == d:
		print("\033[F\r"+t+": ",end="")
		print_bar(1)
		print(" "+str(n)+" / "+str(d))
	else:
		print("\033[F\r"+t+": ",end="")
		print_bar(n/d)
		print(" "+str(n)+" / "+str(d))

swizzleMapCache = {}

# file reading

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
		raise ValueError("invalid int bytesize: "+str(bytes))
	return struct.unpack(parseString,inFile.read(struct.calcsize(parseString)))[0]
def readAndParseIntBig(inFile,bytes,signed=False):
	if bytes == 1:
		parseString = i8CodeB if signed else u8CodeB
	elif bytes == 2:
		parseString = i16CodeB if signed else u16CodeB
	elif bytes == 4:
		parseString = i32CodeB if signed else u32CodeB
	else:
		raise ValueError("invalid int bytesize: "+str(bytes))
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

# https://stackoverflow.com/questions/10689748/how-to-read-bits-from-a-file
# tweaked to operate directly on a bytearray so an extra file-like object isn't needed
# as normal, 0x30 is read as 0, 0, 1, 1, 0, 0, 0, 0 in 1-bit chunks, and as 0011, 0000 in 4-bit chunks
# as reversed, 0x30 is read as 0, 0, 0, 0, 1, 1, 0, 0 in 1-bit chunks, but as 0011, 0000 in 4-bit chunks
# the "why" is simply "because that's how it needs to work" (mostly for BC7 purposes)
class BitReader():
	def __init__(self,a,reverse=False):
		self.input = a
		self.accumulator = 0
		self.bcount = 0
		self.pointer = 0
		self.reverse = reverse
	def _readbit(self):
		if not self.bcount:
			next = self.input[self.pointer]
			self.pointer += 1
			self.accumulator = next
			self.bcount = 8
		if self.reverse:
			rv = (self.accumulator & (1 << 7-(self.bcount-1))) >> 7-(self.bcount-1)
		else:
			rv = (self.accumulator & (1 << self.bcount-1)) >> self.bcount-1
		self.bcount -= 1
		return rv
	def readbits(self,n):
		if n == 0: return None # having to deal with None is better than confusing "read a 0" with "read nothing so here's 0"
		v = 0
		d = n
		while d > 0:
			v = (v << 1) | self._readbit()
			d -= 1
		if self.reverse:
			return reverse_int(v,n)
		return v

# class helper functions

def calculateGlobalBoneMatrixes(boneList):
	localMats = {}
	globalMats = {}
	for b in boneList:
		if b.getIndex() in localMats.keys():
			raise ValueError("Multiple bones with index "+str(b.getIndex())+" in list")
		localMats[b.getIndex()] = [b.getParent(),mathutils.Matrix.LocRotScale(b.getPosition()[0:3],mathutils.Quaternion(b.getRotation()),b.getScale()[0:3])]
	# assumption: bones will only be parented to a previous bone (never a yet-to-be-seen one)
	for b,[p,mtx] in localMats.items():
		if p == -1: # no parent, no transformation
			globalMats[b] = mtx
		else:
			parentMtx = globalMats[p]
			globalMats[b] = parentMtx @ mtx
	return globalMats

# Blender helper functions

def flipRoll(roll):
	return roll % rad360 - rad180

def clampRoll(roll,angleEpsilon):
	# limits roll to being between -180 and +180
	while roll > rad180: roll -= rad180
	while roll < -rad180: roll += rad180
	if abs(roll) < angleEpsilon:
		roll = 0
	return roll

def clampBoneRoll(editBone,angleEpsilon):
	editBone.roll = clampRoll(editBone.roll,angleEpsilon)

def mirrorBone(editBone,otherBone):
	# replaces editBone's position and rotation with a mirrored version of otherBone's
	editBone.head = otherBone.head * mathutils.Vector((-1,1,1))
	editBone.tail = otherBone.tail * mathutils.Vector((-1,1,1))
	editBone.roll = -otherBone.roll

def isBonePairIdentical(thisBone,otherBone,positionEpsilon,angleEpsilon,mirrorable=False):
	# the logic: would the one bone equal the other bone within epsilon?
	# the metrics are head position, angle between Y-axes (facing direction), and angle between Z-axes (roll)
	pos1 = thisBone.head
	pos2 = otherBone.head
	if mirrorable:
		pos1 = pos1 * mathutils.Vector((-1,1,1))
	for p in range(3):
		posDiff = abs(pos1[p] - pos2[p])
		if posDiff >= positionEpsilon:
			return False,"position["+str(p)+"] diff. of "+str(posDiff)+" (out of tolerance by "+str(positionEpsilon-posDiff)+")"
	vector1 = thisBone.y_axis
	vector2 = otherBone.y_axis
	if mirrorable:
		vector1 = vector1 @ mathutils.Matrix([[-1,0,0],[0,1,0],[0,0,1]])
	angleDiff = vector1.angle(vector2)
	if mirrorable:
		if angleDiff > rad90: angleDiff = abs(rad180 - angleDiff) # both "0 degrees apart" and "180 degrees apart" are correct for mirroring (to account for potential flipping)
	if (angleDiff >= angleEpsilon):
		return False,"facing vector angle diff. of "+str(math.degrees(angleDiff))+"d (out of tolerance by "+str(math.degrees(angleEpsilon-angleDiff))+"d)"
	vector1 = thisBone.z_axis
	vector2 = otherBone.z_axis
	if mirrorable:
		vector1 = vector1 @ mathutils.Matrix([[-1,0,0],[0,1,0],[0,0,1]])
	angleDiff = vector1.angle(vector2)
	if mirrorable:
		if angleDiff > rad90: angleDiff = abs(rad180 - angleDiff) # same as above
	if (angleDiff >= angleEpsilon):
		return False,"roll angle diff. of "+str(math.degrees(angleDiff))+"d (out of tolerance by "+str(math.degrees(angleEpsilon-angleDiff))+"d)"
	return True,""

def create_armature_from_bones(boneList,name,pos,rot,boneSize,positionEpsilon,angleEpsilon):
	if isinstance(boneList,MonadoForgeSkeleton): # this way either "a Forge skeleton object" or "a list of Forge bone objects" can be used
		boneList = boneList.getBones()
	bpy.ops.object.select_all(action="DESELECT")
	bpy.ops.object.armature_add(enter_editmode=True, align="WORLD", location=pos, rotation=rot, scale=(1,1,1))
	skelObj = bpy.context.view_layer.objects.active
	skeleton = skelObj.data
	skeleton.show_names = True
	# delete the default bone to start with
	bpy.ops.armature.select_all(action="SELECT")
	bpy.ops.armature.delete()
	# start adding
	editBones = skeleton.edit_bones
	for b in boneList:
		# assumption: no bone will ever precede its parent (i.e. the parent will always be there already to attach to, no second pass needed)
		newBone = editBones.new(b.getName())
		newBone.length = boneSize
		newBone.parent = editBones[b.getParent()] if b.getParent() != 0xffff else None
		parentMatrix = newBone.parent.matrix if newBone.parent else mathutils.Matrix.Identity(4)
		posMatrix = mathutils.Matrix.Translation(b.getPosition())
		rotMatrix = mathutils.Quaternion(b.getRotation()).to_matrix()
		rotMatrix.resize_4x4()
		newBone.matrix = parentMatrix @ (posMatrix @ rotMatrix)
		newBone.length = boneSize # have seen odd non-rounding when not doing this
		# put "normal" bones in layer 1 and endpoints in layer 2
		# must be done in this order or the [0] set will be dropped because bones must be in at least one layer
		newBone.layers[1] = b.isEndpoint()
		newBone.layers[0] = not b.isEndpoint()
	# now that the bones are in, spin them around so they point in a more logical-for-Blender direction
	for b in editBones:
		# transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
		b.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix())
		# change from +X being the "main axis" (game format) to +Y (Blender format)
		b.matrix = b.matrix @ mathutils.Matrix([[0,1,0,0],[0,0,1,0],[1,0,0,0],[0,0,0,1]])
		# now apply epsilons
		# part 1: if a position is close enough to 0, make it 0
		b.head = [(0 if abs(p) < positionEpsilon else p) for p in b.head]
		b.tail = [(0 if abs(p) < positionEpsilon else p) for p in b.tail]
		# part 2: if a tail position is close enough to the head position, make it equal
		newTail = b.tail
		for i in range(3):
			h = b.head[i]
			t = b.tail[i]
			if abs(h-t) < positionEpsilon:
				newTail[i] = h
		b.tail = newTail
		# part 3: if the roll is close enough to 0, make it 0
		clampBoneRoll(b,angleEpsilon)
	skelObj.name = name
	skelObj.data.name = name
	bpy.ops.armature.select_all(action="DESELECT")
	bpy.ops.object.mode_set(mode="OBJECT")
	return skelObj # return the new object

def cleanup_mesh(context,meshObj,looseVerts,emptyGroups,emptyColours,emptyShapes):
	tempActive = context.view_layer.objects.active
	context.view_layer.objects.active = meshObj
	meshData = meshObj.data
	# remove all the vertices without faces attached (there can be a lot and it's apparently hard to do in any other way)
	if looseVerts:
		bpy.ops.object.mode_set(mode="EDIT")
		with redirect_stdout(io.StringIO()): # hide "X verts deleted" output
			bpy.ops.mesh.delete_loose(use_verts=True,use_edges=False,use_faces=False)
		bpy.ops.object.mode_set(mode="OBJECT")
	# clean up vertex groups that have nothing in them
	if emptyGroups:
		unusedVertexGroups = [g.name for g in meshObj.vertex_groups]
		for v in meshData.vertices:
			for g in v.groups:
				try: unusedVertexGroups.remove(meshObj.vertex_groups[g.group].name)
				except ValueError: pass
		for g in unusedVertexGroups:
			meshObj.vertex_groups.remove(meshObj.vertex_groups[g])
	# remove vertex colours if they're pure white or black with pure 1.0 or 0.0 alpha
	# a colour layer like this conveys no information, so make it clear it's useless by removing it
	if emptyColours:
		coloursArray = [[1.0,1.0,1.0,1.0],[1.0,1.0,1.0,0.0],[0.0,0.0,0.0,1.0],[0.0,0.0,0.0,0.0]]
		coloursToRemove = []
		for layer in meshData.color_attributes:
			empty = True
			first = list(layer.data[0].color)
			if first not in coloursArray:
				empty = False
			else:
				for c in layer.data:
					if list(c.color) != first: # if any single one does not match the first, this is not a useless layer
						empty = False
						break
			if empty:
				coloursToRemove.append(layer)
		for layer in coloursToRemove:
			meshData.color_attributes.remove(layer)
	# determine which shapes don't do anything and remove them
	# seems to be somewhat conservative (some shapes with no visible effect are kept), but that's the safer error to make
	if emptyShapes:
		keysToRemove = []
		for s in meshData.shape_keys.key_blocks:
			if s.name == "basis": continue
			isEmpty = True
			for v in range(len(meshData.vertices)):
				if meshData.vertices[v].co != s.data[v].co:
					isEmpty = False
			if isEmpty:
				keysToRemove.append(s)
		for r in keysToRemove:
			meshObj.shape_key_remove(r)
	context.view_layer.objects.active = tempActive

def register():
	pass

def unregister():
	pass

#[...]