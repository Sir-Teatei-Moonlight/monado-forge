import bpy
import math
import mathutils
import struct

rad90 = math.radians(90)
rad180 = math.radians(180)
rad360 = math.radians(360)
rad720 = math.radians(720)

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

class MonadoForgeBone:
	def __init__(self):
		self._name = "Bone"
		self._parent = -1
		self._position = [0,0,0,1] # x, y, z, w
		self._rotation = [0,0,0,1] # w, x, y, z
		self._scale = [1,1,1,1] # x, y, z, w
		self._endpoint = False
	
	def getName(self):
		return self._name
	def setName(self,x):
		if not isinstance(x,str):
			raise TypeError("expected a string, not a(n) "+str(type(x)))
		self._name = x
	
	def getParent(self):
		return self._parent
	def setParent(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._parent = x
	
	def getPos(self):
		return self._position
	def setPos(self,a):
		if len(a) == 4:
			self._position = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	
	def getRot(self):
		return self._rotation
	def setRot(self,a):
		if len(a) == 4:
			self._rotation = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	
	def getScl(self):
		return self._scale
	def setScl(self,a):
		if len(a) == 4:
			self._scale = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	
	def isEndpoint(self):
		return self._endpoint
	def setEndpoint(self,x):
		if not isinstance(x,bool):
			raise TypeError("expected a bool, not a(n) "+str(type(x)))
		self._endpoint = x

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
	if angleDiff > rad90: angleDiff = abs(rad180 - angleDiff) # both "0 degrees apart" and "180 degrees apart" are correct for mirroring (to account for potential flipping)
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

def create_armature_from_bones(boneList,name,boneSize,positionEpsilon,angleEpsilon):
	bpy.ops.object.select_all(action="DESELECT")
	bpy.ops.object.armature_add(enter_editmode=True, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
	skeleton = bpy.context.view_layer.objects.active.data
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
		posMatrix = mathutils.Matrix.Translation(b.getPos())
		rotMatrix = mathutils.Quaternion(b.getRot()).to_matrix()
		rotMatrix.resize_4x4()
		newBone.matrix = parentMatrix @ (posMatrix @ rotMatrix)
		newBone.length = boneSize # have seen odd non-rounding when not doing this
		# put "normal" bones in layer 1 and endpoints in layer 2
		# must be done in this order or the [0] set will be dropped because bones must be in at least one layer
		newBone.layers[1] = b.isEndpoint()
		newBone.layers[0] = not b.isEndpoint()
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
	bpy.context.view_layer.objects.active.name = name
	bpy.context.view_layer.objects.active.data.name = name
	bpy.ops.armature.select_all(action="DESELECT")
	bpy.ops.object.mode_set(mode="OBJECT")

class MonadoForgeVertex:
	def __init__(self,p,n=None,c=None,w={}):
		if len(p) != 3: raise ValueError("sequence must be length 3, not "+str(len(p)))
		self._position = p[:]
		self._normal = n
		self._colour = c
		self._weights = w
	
	def getPos(self):
		return self._position
	def setPos(self,a):
		if len(a) == 4:
			self._position = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	
	def getNrm(self):
		return self._normal
	def clearNrm(self):
		self._normal = None
	def setNrm(self,a):
		if len(a) == 3:
			self._normal = a[:]
		else:
			raise ValueError("sequence must be length 3, not "+str(len(a)))
	
	def getCol(self):
		return self._colour
	def clearCol(self):
		self._colour = None
	def setCol(self,a):
		if len(a) == 3 or len(a) == 4: # allow for the chance of alpha colours
			self._colour = a[:]
		else:
			raise ValueError("sequence must be length 3 or 4, not "+str(len(a)))
	
	def getWeights(self):
		return self._weights
	def getWeight(self,name):
		return self._weights[name]
	def clearWeights(self):
		self._weights = {}
	def addWeight(self,name,value):
		self._weights[name] = value

# probably don't really need this one but it's consistent to have
class MonadoForgeEdge:
	def __init__(self,v1,v2):
		self._vert1 = v1
		self._vert2 = v2

class MonadoForgeFace:
	def __init__(self,v,mi=0):
		self._verts = v[:]
		self._materialIndex = mi

class MonadoForgeMesh:
	def __init__(self):
		self._name = "Mesh"
		self._vertices = []
		self._edges = []
		self._faces = []

class MonadoForgePackage:
	def __init__(self):
		self._bones = []
	
	def getBones(self):
		return self._bones
	def clearBones(self):
		self._bones = []
	def addBone(self,bone):
		self._bones.append(bone)
	def setBones(self,bones):
		self._bones = bones[:]

def register():
	pass

def unregister():
	pass

#[...]