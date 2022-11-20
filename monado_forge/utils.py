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
	
	def setName(self,x):
		if not isinstance(x,str):
			raise TypeError("expected a string, not a(n) "+str(type(x)))
		self._name = x
	def getName(self):
		return self._name
	
	def setParent(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._parent = x
	def getParent(self):
		return self._parent
	
	def setPos(self,a):
		if len(a) == 4:
			self._position = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	def getPos(self):
		return self._position
	
	def setRot(self,a):
		if len(a) == 4:
			self._rotation = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	def getRot(self):
		return self._rotation
	
	def setScl(self,a):
		if len(a) == 4:
			self._scale = a[:]
		else:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
	def getScl(self):
		return self._scale
	
	def setEndpoint(self,x):
		if not isinstance(x,bool):
			raise TypeError("expected a bool, not a(n) "+str(type(x)))
		self._endpoint = x
	def isEndpoint(self):
		return self._endpoint

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

#[...]