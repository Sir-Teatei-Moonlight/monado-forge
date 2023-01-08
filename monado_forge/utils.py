import bpy
import io
import math
import mathutils
import numpy
import os
import struct
from contextlib import redirect_stdout

# math constants

rad90 = math.radians(90)
rad180 = math.radians(180)
rad360 = math.radians(360)
rad720 = math.radians(720)

# useful stuff

def clamp(value,low,high):
	return max(low,min(value,high))
# ceiling division (as opposed to "//" floor division)
# https://stackoverflow.com/questions/14822184/
def ceildiv(a,b):
	return -(a // -b)
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
	roll = editBone.roll
	editBone.matrix = otherBone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
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

def create_armature_from_bones(boneList,name,boneSize,positionEpsilon,angleEpsilon):
	bpy.ops.object.select_all(action="DESELECT")
	bpy.ops.object.armature_add(enter_editmode=True, align="WORLD", location=(0,0,0), rotation=(0,0,0), scale=(1,1,1))
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
		b.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix()) # transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
		roll = b.y_axis # roll gets lost after the following matrix mult for some reason, so preserve it
		b.matrix = b.matrix @ mathutils.Matrix([[0,1,0,0],[1,0,0,0],[0,0,1,0],[0,0,0,1]]) # change from +X being the "main axis" to +Y
		b.align_roll(roll)
		# everything done, now apply epsilons
		b.head = [(0 if abs(p) < positionEpsilon else p) for p in b.head]
		b.tail = [(0 if abs(p) < positionEpsilon else p) for p in b.tail]
		clampBoneRoll(b,angleEpsilon)
	skelObj.name = name
	skelObj.data.name = name
	bpy.ops.armature.select_all(action="DESELECT")
	bpy.ops.object.mode_set(mode="OBJECT")
	return skelObj # return the new object

def cleanup_mesh(context,meshObj,looseVerts,emptyGroups,emptyShapes):
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

# https://learn.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
# uses the "raw" values taken from the code rather than the ones in the MS enum (we aren't calling any MS code so we don't need it)
# only contains things we know of (rather than future-proofing with extra entries) since how're we supposed to guess what the raw numbers equate to
# [formatName, bitsPerPixel]
imageFormats = {
				37:["R8G8B8A8_UNORM",32],
				66:["BC1_UNORM",4], # aka DXT1
				68:["BC3_UNORM",8], # aka DXT5
				73:["BC4_UNORM",4],
				75:["BC5_UNORM",8],
				77:["BC7_UNORM",8],
				}

# much of this is just grabbed from XBC2MD, but only after understanding it (rather than blindly copy-pasting anything)
# REMINDER: don't manipulate image.pixels directly/individually or things will be dummy slow https://blender.stackexchange.com/questions/3673/
# references:
# 	https://www.vg-resource.com/thread-31389.html
# 	https://www.vg-resource.com/thread-33929.html
# 	https://en.wikipedia.org/wiki/Z-order_curve
# 	https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression
# 	https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format
# 	https://github.com/python-pillow/Pillow/blob/main/src/libImaging/BcnDecode.c
# 	https://github.com/ScanMountGoat/tegra_swizzle
def parse_texture(textureName,imgVersion,imgType,imgWidth,imgHeight,rawData,blueBC5,overwrite=True,saveTo=None):
	try:
		format,bitsPerPixel = imageFormats[imgType]
	except KeyError:
		raise ValueError("unsupported image type: id# "+str(imgType))
	if format in ["BC7_UNORM"]:
		print_warning("Format "+format+" is not yet supported (texture "+textureName+" will be blank)")
	
	# first, check to see if image of the intended name exists already, and how to proceed
	try:
		existingImage = bpy.data.images[textureName]
		if overwrite:
			bpy.data.images.remove(existingImage)
	except KeyError as e: # no existing image of the same name
		pass # fine, move on
	newImage = bpy.data.images.new(textureName,imgWidth,imgHeight)
	# don't really want to do any of this until the end, but apparently setting the filepath after setting the pixels clears the image for no good reason
	newImage.file_format = "PNG"
	if saveTo:
		newImage.filepath = os.path.join(saveTo,textureName+".png")
	
	blockSize = 4 # in pixels
	unswizzleBufferSize = bitsPerPixel*2 # needs a better name at some point
	if format == "R8G8B8A8_UNORM": # blocks are single pixels rather than 4x4
		blockSize = 1
		unswizzleBufferSize = bitsPerPixel // 8
	# since the minimum block size is 4, images must be divisible by 4 - extend them as necessary
	virtImgWidth = imgWidth if imgWidth % blockSize == 0 else imgWidth + (blockSize - (imgWidth % blockSize))
	virtImgHeight = imgHeight if imgHeight % blockSize == 0 else imgHeight + (blockSize - (imgHeight % blockSize))
	# gotta create the image in full emptiness to start with, so we can random-access-fill the blocks as they come
	# Blender always needs alpha, so colours must be length 4
	pixels = numpy.zeros([virtImgHeight*virtImgWidth,4],dtype=float)
	
	blockCountX = virtImgWidth // blockSize
	blockCountY = virtImgHeight // blockSize
	blockCount = blockCountX*blockCountY
	tileWidth = clamp(16 // unswizzleBufferSize, 1, 16)
	tileCountX = ceildiv(blockCountX,tileWidth)
	tileCountY = blockCountY # since tile height is always 1
	tileCount = tileCountX*tileCountY
	# essentially, how many unswizzled "rows" must we read to get a full "column" (in tiles)
	# this controls how wide the column chunk must be
	# not currently used (dunno if it later needs to be)
	columnStackSize = clamp(blockCountY // 8, 1, 16)
	
	d = io.BytesIO(rawData)
	#print(format)
	
	try:
		swizzlist = swizzleMapCache[f"{tileCountY},{tileCountX}"]
	except KeyError:
		swizzleTileMap = numpy.full([tileCountY,tileCountX],-1,dtype=int)
		# swizzle pattern: (may need to change as larger images are discovered, but should be correct for smaller ones)
		# x = 10001111111000010010
		# y = 01110000000111101101
		# [x9, y9, y8, y7, x8, x7, x6, x5, x4, x3, x2, y6, y5, y4, y3, x1, y2, y1, x0, y0]
		# the distinction between z and currentTile is so we can draw the z-curve out of bounds while keeping all valid values in-bounds
		currentTile = 0
		z = -1 # will be incremented to 0 shortly
		while currentTile < tileCountY*tileCountX:
			if z > 10000000:
				print_error("Bad z-loop detected in image "+textureName+": z = "+str(z)+"; currentTile = "+str(currentTile))
				break
			z += 1
			y = ((z&0x70000)>>9) | ((z&0x1E0)>>2) | ((z&0xC)>>1) | (z&0x1)
			if y >= len(swizzleTileMap): continue
			x = ((z&0x80000)>>10) | ((z&0xFE00)>>7) | ((z&0x10)>>3) | ((z&0x2)>>1)
			if x >= len(swizzleTileMap[y]): continue
			swizzleTileMap[y,x] = currentTile
			currentTile += 1
		swizzlist = swizzleTileMap.flatten().tolist()
		swizzleMapCache[f"{tileCountY},{tileCountX}"] = swizzlist
		#print(swizzlist)
	#swizzlist = range(blockCountX*blockCountY) # no-op option for debugging
	monochrome = True
	unassignedCount = False
	for t in range(tileCount):
		if swizzlist[t] == -1:
			unassignedCount += 1
			continue
		d.seek(swizzlist[t]*(unswizzleBufferSize*tileWidth))
		for t2 in range(tileWidth):
			targetTile = t
			targetBlock = t*tileWidth + t2
			if targetBlock >= blockCount: continue # can happen for tiny textures, not a problem
			targetBlockX = targetBlock % blockCountX
			targetBlockY = targetBlock // blockCountX
			# convert block to pixel (Y is inverted, X is not)
			blockRootPixelX = targetBlockX*blockSize
			blockRootPixelY = virtImgHeight - targetBlockY*blockSize - blockSize
			if format == "R8G8B8A8_UNORM":
				r = readAndParseInt(d,1)
				g = readAndParseInt(d,1)
				b = readAndParseInt(d,1)
				a = readAndParseInt(d,1)
				pixels[blockRootPixelX+blockRootPixelY*virtImgWidth] = [r/255.0,g/255.0,b/255.0,a/255.0]
			elif format == "BC1_UNORM" or format == "BC3_UNORM": # easy enough to treat these the same
				if format == "BC3_UNORM":
					a0 = readAndParseInt(d,1)
					a1 = readAndParseInt(d,1)
					alphas = [a0,a1]
					if a0 > a1:
						for a in range(6):
							alphas.append(((6-a)*a0+(a+1)*a1)/7.0)
					else:
						for a in range(4):
							alphas.append(((4-a)*a0+(a+1)*a1)/5.0)
						alphas.append(0.0)
						alphas.append(255.0)
					alphaIndexes0 = int.from_bytes(d.read(3),"little") # can't use readAndParseInt for these since 3 is a weird size
					alphaIndexes1 = int.from_bytes(d.read(3),"little")
					alphaIndexesTemp = []
					for a in range(8):
						alphaIndexesTemp.append((alphaIndexes0 & (0b111 << a*3)) >> a*3)
					for a in range(8):
						alphaIndexesTemp.append((alphaIndexes1 & (0b111 << a*3)) >> a*3)
					alphaIndexes = [alphaIndexesTemp[i] for i in [12,13,14,15,8,9,10,11,4,5,6,7,0,1,2,3]]
				else:
					alphas = [255.0 for i in range(8)]
					alphaIndexes = [0 for i in range(16)]
				endpoint0 = readAndParseInt(d,2)
				endpoint1 = readAndParseInt(d,2)
				row0 = readAndParseInt(d,1)
				row1 = readAndParseInt(d,1)
				row2 = readAndParseInt(d,1)
				row3 = readAndParseInt(d,1)
				r0,g0,b0 = ((endpoint0 & 0b1111100000000000) >> 11),((endpoint0 & 0b0000011111100000) >> 5),(endpoint0 & 0b0000000000011111)
				r1,g1,b1 = ((endpoint1 & 0b1111100000000000) >> 11),((endpoint1 & 0b0000011111100000) >> 5),(endpoint1 & 0b0000000000011111)
				# potential future feature: autodetect images that are supposed to be greyscale and only use the higher-resolution green channel
				#if monochrome and not(r0 == b0 and r1 == b1 and abs(r0*2 - g0) <= 1 and abs(r1*2 - g1) <= 1):
				#	monochrome = False
				colours = [[],[],[],[]]
				colours[0] = [r0/0b11111,g0/0b111111,b0/0b11111,1.0]
				colours[1] = [r1/0b11111,g1/0b111111,b1/0b11111,1.0]
				if endpoint0 > endpoint1 or format == "BC3_UNORM":
					colours[2] = [2/3*colours[0][0]+1/3*colours[1][0],2/3*colours[0][1]+1/3*colours[1][1],2/3*colours[0][2]+1/3*colours[1][2],1.0]
					colours[3] = [1/3*colours[0][0]+2/3*colours[1][0],1/3*colours[0][1]+2/3*colours[1][1],1/3*colours[0][2]+2/3*colours[1][2],1.0]
				else:
					colours[2] = [1/2*colours[0][0]+1/2*colours[1][0],1/2*colours[0][1]+1/2*colours[1][1],1/2*colours[0][2]+1/2*colours[1][2],1.0]
					colours[3] = [0.0,0.0,0.0,0.0]
				pixelIndexes = [
								(row3 & 0b00000011), (row3 & 0b00001100) >> 2, (row3 & 0b00110000) >> 4, (row3 & 0b11000000) >> 6,
								(row2 & 0b00000011), (row2 & 0b00001100) >> 2, (row2 & 0b00110000) >> 4, (row2 & 0b11000000) >> 6,
								(row1 & 0b00000011), (row1 & 0b00001100) >> 2, (row1 & 0b00110000) >> 4, (row1 & 0b11000000) >> 6,
								(row0 & 0b00000011), (row0 & 0b00001100) >> 2, (row0 & 0b00110000) >> 4, (row0 & 0b11000000) >> 6,
								]
				for p,pi in enumerate(pixelIndexes):
					pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = colours[pi][0:3]+[alphas[alphaIndexes[p]]/255.0]
			elif format == "BC4_UNORM" or format == "BC5_UNORM": # BC5 is just two BC4s stapled together
				r0 = readAndParseInt(d,1)
				r1 = readAndParseInt(d,1)
				reds = [r0,r1]
				if r0 > r1:
					for r in range(6):
						reds.append(((6-r)*r0+(r+1)*r1)/7.0)
				else:
					for r in range(4):
						reds.append(((4-r)*r0+(r+1)*r1)/5.0)
					reds.append(0.0)
					reds.append(255.0)
				redIndexes0 = int.from_bytes(d.read(3),"little") # can't use readAndParseInt for these since 3 is a weird size
				redIndexes1 = int.from_bytes(d.read(3),"little")
				redIndexes = []
				for r in range(8):
					redIndexes.append((redIndexes0 & (0b111 << r*3)) >> r*3)
				for r in range(8):
					redIndexes.append((redIndexes1 & (0b111 << r*3)) >> r*3)
				if format == "BC4_UNORM":
					pixelIndexes = [redIndexes[i] for i in [12,13,14,15,8,9,10,11,4,5,6,7,0,1,2,3]]
					for p,pi in enumerate(pixelIndexes):
						value = reds[pi[0]]/255.0
						colour = [value,value,value,1]
						pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = colour
				else: # is BC5_UNORM
					g0 = readAndParseInt(d,1)
					g1 = readAndParseInt(d,1)
					greens = [g0,g1]
					if g0 > g1:
						for g in range(6):
							greens.append(((6-g)*g0+(g+1)*g1)/7.0)
					else:
						for g in range(4):
							greens.append(((4-g)*g0+(g+1)*g1)/5.0)
						greens.append(0.0)
						greens.append(255.0)
					greenIndexes0 = int.from_bytes(d.read(3),"little")
					greenIndexes1 = int.from_bytes(d.read(3),"little")
					greenIndexes = []
					for g in range(8):
						greenIndexes.append((greenIndexes0 & (0b111 << g*3)) >> g*3)
					for g in range(8):
						greenIndexes.append((greenIndexes1 & (0b111 << g*3)) >> g*3)
					pixelIndexes = [[redIndexes[i],greenIndexes[i]] for i in [12,13,14,15,8,9,10,11,4,5,6,7,0,1,2,3]]
					for p,pi in enumerate(pixelIndexes):
						if blueBC5: # calculate blue channel for normal mapping (length of [r,g,b] is 1.0)
							r = (reds[pi[0]]-128)/128.0
							g = (greens[pi[1]]-128)/128.0
							try:
								b = (math.sqrt(1-r**2-g**2))/2+0.5
							except ValueError: # r**2-g**2 > 1, thus sqrt tries to operate on a negative
								b = 0.5
						else:
							b = 0
						colour = [reds[pi[0]]/255.0,greens[pi[1]]/255.0,b,1]
						pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = colour
	if unassignedCount > 0:
		print_error("Texture "+textureName+" didn't complete deswizzling correctly: "+str(unassignedCount)+" / "+str(tileCountY*tileCountX)+" tiles unassigned")
	d.close()
	
	# final pixel data must be flattened (and, if necessary, cropped)
	newImage.pixels = pixels.reshape([virtImgHeight,virtImgWidth,4])[0:imgHeight,0:imgWidth].flatten()
	newImage.update()
	if saveTo:
		newImage.save()
	return None

# Forge classes, because just packing/unpacking arrays gets old and error-prone

class MonadoForgeBone:
	def __init__(self):
		self._name = "Bone"
		self._parent = -1
		self._position = [0,0,0,1] # x, y, z, w
		self._rotation = [1,0,0,0] # w, x, y, z
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
	def clearParent(self):
		self._parent = -1
	def setParent(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._parent = x
	
	def getPosition(self):
		return self._position
	def setPosition(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._position = a[:]
	
	def getRotation(self):
		return self._rotation
	def setRotation(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._rotation = a[:]
	
	def getScale(self):
		return self._scale
	def setScale(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._scale = a[:]
	
	def isEndpoint(self):
		return self._endpoint
	def setEndpoint(self,x):
		if not isinstance(x,bool):
			raise TypeError("expected a bool, not a(n) "+str(type(x)))
		self._endpoint = x

class MonadoForgeSkeleton:
	def __init__(self):
		self._bones = []
	
	def getBones(self):
		return self._bones
	def clearBones(self):
		self._bones = []
	def addBone(self,bone):
		if not isinstance(bone,MonadoForgeBone):
			raise TypeError("expected a MonadoForgeBone, not a(n) "+str(type(bone)))
		self._bones.append(bone)
	def setBones(self,bones):
		self.clearBones()
		for b in bones: self.addBone(b)

class MonadoForgeVertex:
	def __init__(self):
		self._id = -1
		self._position = [0,0,0] # having position ever be None seems to cause Problems
		self._uvs = {}
		self._normal = None
		self._colour = None
		self._weightSetIndex = -1 # pre-bake
		self._weights = {} # post-bake (must also be by index rather than name sicne we don't necessarily know names)
	
	def getID(self):
		return self._id
	# only set by the parent mesh
	
	def getPosition(self):
		return self._position
	def setPosition(self,a):
		if len(a) != 3:
			raise ValueError("sequence must be length 3, not "+str(len(a)))
		self._position = a[:]
	# there is no "clearPosition" because of the None problem
	
	def hasUVs(self):
		return self._uvs != {}
	def getUVs(self):
		return self._uvs
	def getUV(self,layer):
		return self._uvs[layer]
	def clearUVs(self):
		self._uvs = {}
	def setUV(self,layer,value):
		if len(value) != 2:
			raise ValueError("sequence must be length 2, not "+str(len(value)))
		self._uvs[layer] = value
	
	def hasNormal(self):
		return self._normal != None
	def getNormal(self):
		return self._normal
	def clearNormal(self):
		self._normal = None
	def setNormal(self,a):
		if len(a) != 3:
			raise ValueError("sequence must be length 3, not "+str(len(a)))
		self._normal = a[:]
	
	def hasColour(self):
		return self._colour != None
	def getColour(self):
		return self._colour
	def clearColour(self):
		self._colour = None
	def setColour(self,a):
		if len(a) != 4: # allow alpha colours
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._colour = a[:]
	
	def hasWeightIndex(self):
		return self._weightSetIndex != -1
	def getWeightSetIndex(self):
		return self._weightSetIndex
	def clearWeightSetIndex(self):
		self._weightSetIndex = -1
	def setWeightSetIndex(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._weightSetIndex = x
	
	def hasWeights(self):
		return self._weights != {}
	def getWeights(self):
		return self._weights
	def getWeight(self,groupIndex):
		return self._weights[groupIndex]
	def clearWeights(self):
		self._weights = {}
	def setWeight(self,groupIndex,value):
		if not isinstance(groupIndex,int):
			raise TypeError("expected an int, not a(n) "+str(type(groupIndex)))
		if not isinstance(value,float):
			raise TypeError("expected a float, not a(n) "+str(type(value)))
		self._weights[groupIndex] = value

class MonadoForgeFace:
	def __init__(self):
		self._vertexIndexes = []
		self._materialIndex = 0
	
	def getVertexIndexes(self):
		return self._vertexIndexes
	def clearVertexIndexes(self):
		self._vertexIndexes = []
	def addVertexIndex(self,v):
		if not isinstance(v,int):
			raise TypeError("expected an int, not a(n) "+str(type(v)))
		self._vertexIndexes.append(v)
	def setVertexIndexes(self,a):
		if not isinstance(a,list):
			raise TypeError("expected a list, not a(n) "+str(type(a)))
		self._vertexIndexes = a[:]

class MonadoForgeMeshShape:
	def __init__(self):
		self._vtIndex = 0
		self._vertices = {} # indexes are not necessarily in order or sequential, so must be a dict (by index) rather than a plain list
		self._name = ""
	
	def getVertexTableIndex(self):
		return self._vtIndex
	def setVertexTableIndex(self,i):
		self._vtIndex = i
	
	def getVertices(self):
		return self._vertices
	def clearVertices(self):
		self._vertices = {}
	def addVertex(self,i,v):
		self._vertices[i] = v
	def setVertices(self,a):
		self._vertices = a
	
	def getName(self):
		return self._name
	def setName(self,x):
		if not isinstance(x,str):
			raise TypeError("expected a string, not a(n) "+str(type(x)))
		self._name = x

class MonadoForgeMesh:
	def __init__(self):
		self._name = "Mesh"
		self._vertices = []
		self._faces = []
		self._weightSets = {} # because it can be convenient to hold these here and have vertexes just refer with index
		self._shapes = [] # list of MonadoForgeMeshShapes
	
	def getVertices(self):
		return self._vertices
	def clearVertices(self):
		self._vertices = []
	def addVertex(self,v):
		if not isinstance(v,MonadoForgeVertex):
			raise TypeError("expected a MonadoForgeVertex, not a(n) "+str(type(v)))
		self._vertices.append(v)
	def setVertices(self,a):
		self._vertices = []
		for v in a: self.addVertex(v)
	
	def getFaces(self):
		return self._faces
	def clearFaces(self):
		self._faces = []
	def addFace(self,f):
		if not isinstance(f,MonadoForgeFace):
			raise TypeError("expected a MonadoForgeFace, not a(n) "+str(type(f)))
		self._faces.append(f)
	def setFaces(self,a):
		self._faces = []
		for f in a: self.addFace(f)
	
	def getWeightSets(self):
		return self._weightSets
	def clearWeightSets(self):
		self._weightSets = []
	def addWeightSet(self,index,a):
		if not isinstance(a,list):
			raise TypeError("expected a list, not a(n) "+str(type(a)))
		self._weightSets[index] = a
	def setWeightSets(self,d):
		if not isinstance(d,dict):
			raise TypeError("expected a dict, not a(n) "+str(type(d)))
		self._weightSets = d
	
	def getShapes(self):
		return self._shapes
	def clearShapes(self):
		self._shapes = []
	def addShape(self,shape):
		if not isinstance(shape,MonadoForgeMeshShape):
			raise TypeError("expected a MonadoForgeMeshShape, not a(n) "+str(type(shape)))
		self._shapes.append(shape)
	def setShapes(self,shapeList):
		self._shapes = []
		for s in shapeList: self.addShape(s)
	
	# assumption: if a single vertex has any of these, all the other vertices must also
	def hasUVs(self):
		for v in self._vertices:
			if v.hasUVs(): return True
		return False
	def hasNormals(self):
		for v in self._vertices:
			if v.hasNormal(): return True
		return False
	def hasColours(self):
		for v in self._vertices:
			if v.hasColour(): return True
		return False
	def hasWeightIndexes(self):
		for v in self._vertices:
			if v.hasWeightIndex(): return True
		return False
	def hasWeights(self):
		for v in self._vertices:
			if v.hasWeights(): return True
		return False
	def hasShapes(self):
		return len(self._shapes) > 0
	
	def indexVertices(self):
		for i,v in enumerate(self._vertices):
			v._id = i
	
	def getVertexPositionsList(self):
		return [v.getPosition() for v in self._vertices]
	def getUVLayerList(self):
		layers = []
		for v in self._vertices:
			layers += [k for k in v.getUVs().keys()]
		return list(set(layers))
	def getVertexUVsLayer(self,layer):
		return [v.getUVs()[layer] for v in self._vertices]
	def getVertexNormalsList(self):
		return [v.getNormal() for v in self._vertices]
	def getVertexColoursList(self):
		return [v.getColour() for v in self._vertices]
	def getVertexWeightIndexesList(self):
		return [v.getWeightSetIndex() for v in self._vertices]
	def getVertexWeightsList(self):
		return [v.getWeights() for v in self._vertices]
	def getVertexesInWeightGroup(self,groupID):
		return [v for v in self._vertices if groupID in v.getWeights().keys()]
	def getFaceVertexIndexesList(self):
		return [f.getVertexIndexes() for f in self._faces]

class MonadoForgeMeshHeader:
	# intended to be immutable, so all the setting is in the constructor
	def __init__(self,id,md,vt,ft,mm,lod):
		self._meshID = id
		self._meshFlags = md
		self._meshVertTableIndex = vt
		self._meshFaceTableIndex = ft
		self._meshMaterialIndex = mm
		self._meshLODValue = lod
	def getMeshID(self):
		return self._meshID
	def getMeshFlags(self):
		return self._meshFlags
	def getMeshVertTableIndex(self):
		return self._meshVertTableIndex
	def getMeshFaceTableIndex(self):
		return self._meshFaceTableIndex
	def getMeshMaterialIndex(self):
		return self._meshMaterialIndex
	def getMeshLODValue(self):
		return self._meshLODValue

# this class is specifically for passing wimdo results to wismt import
# assumption: there can be only one skeleton (it's just a collection of bones technically)
class MonadoForgeWimdoPackage:
	def __init__(self,skel,mh,sh):
		if not isinstance(skel,MonadoForgeSkeleton):
			raise TypeError("expected a MonadoForgeSkeleton, not a(n) "+str(type(skel)))
		if not isinstance(mh,list):
			raise TypeError("expected a list, not a(n) "+str(type(mh)))
		if not isinstance(sh,list):
			raise TypeError("expected a list, not a(n) "+str(type(sh)))
		self._skeleton = skel
		self._meshHeaders = mh
		self._shapeHeaders = sh
	def getSkeleton(self):
		return self._skeleton
	def getMeshHeaders(self):
		return self._meshHeaders
	def getShapeHeaders(self):
		return self._shapeHeaders
	
	def getLODList(self):
		lods = []
		for mh in self._meshHeaders:
			lods.append(mh.getMeshLODValue())
		return list(set(lods))
	def getBestLOD(self):
		return min(self.getLODList())

# this is intended to be used only once everything game-specific is done and the data is fully in agnostic format
class MonadoForgeImportedPackage:
	def __init__(self):
		self._skeletons = []
		self._meshes = []
	
	def getSkeletons(self):
		return self._skeletons
	def clearSkeletons(self):
		self._skeletons = []
	def addSkeleton(self,skeleton):
		self._skeletons.append(skeleton)
	def setSkeletons(self,skeletons):
		self._skeletons = skeletons[:]
	
	def getMeshes(self):
		return self._meshes
	def clearMeshes(self):
		self._meshes = []
	def addMesh(self,mesh):
		self._meshes.append(mesh)
	def setMeshes(self,meshes):
		self._meshes = meshes[:]

def register():
	pass

def unregister():
	pass

#[...]