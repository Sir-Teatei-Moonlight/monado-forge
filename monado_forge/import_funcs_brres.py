import bpy
import io
import math
import mathutils
import os

from . classes import *
from . utils import *
from . utils_img import *
from . import_funcs import *
from . modify_funcs import *

# various sources:
# https://wiki.tockdom.com/wiki/BRRES_(File_Format)
# https://avsys.xyz/wiki/BRRES_(File_Format)
# the raw C++-masquerading-as-C# code of BrawlBox v0.66 (why else would it all be pointers >:( )

def read_brres_str(f,pointer,offset,debug=False):
	crumb = f.tell()
	f.seek(offset+pointer - 4) # have to "back up" 4 to get the length (could just do a till-null read, but this is safer)
	if debug: print(f.tell())
	length = readAndParseIntBig(f,4)
	if length > 0xffff: # sanity check
		print_error("tried to read a string from a bad place: file position "+str(offset+pointer))
		f.seek(crumb)
		return "(bad string "+str(offset+pointer)+")"
	s = readFixedLenStr(f,length)
	f.seek(crumb)
	return s

# output: a dict of name : offset (absolute)
def parse_brres_dict(f,prefix=""):
	headerCrumb = f.tell()
	dictSize = readAndParseIntBig(f,4) # includes this header
	dictCount = readAndParseIntBig(f,4)
	d = {}
	for i in range(dictCount+1): # the +1 is because there's always an extra reference entry to begin with
		id = readAndParseIntBig(f,2)
		unk1 = readAndParseIntBig(f,2)
		leftIndex = readAndParseIntBig(f,2)
		rightIndex = readAndParseIntBig(f,2)
		namePointer = readAndParseIntBig(f,4)
		dataPointer = readAndParseIntBig(f,4)
		
		# current belief is that the ID and L/R indexes aren't needed for our purposes
		
		name = None
		dataPos = None
		if namePointer > 0:
			name = read_brres_str(f,namePointer,headerCrumb)
		if dataPointer > 0:
			dataPos = dataPointer + headerCrumb
		if name and dataPos:
			d[prefix+name] = dataPos
	actualSize = f.tell() - headerCrumb
	if actualSize != dictSize:
		print_warning("dict at "+str(headerCrumb)+" has malformed size: expected "+str(dictSize)+", got "+str(actualSize))
	return d

def parse_mdl0(f, context, subfileOffset):
	printProgress = context.scene.monado_forge_main.printProgress
	subfileLength = readAndParseIntBig(f,4)
	subfileVersion = readAndParseIntBig(f,4)
	subfileParentOffset = readAndParseIntBig(f,4,signed=True)
	definitionsOffset = readAndParseIntBig(f,4)
	bonesOffset = readAndParseIntBig(f,4)
	positionsOffset = readAndParseIntBig(f,4)
	normalsOffset = readAndParseIntBig(f,4)
	coloursOffset = readAndParseIntBig(f,4)
	uvsOffset = readAndParseIntBig(f,4)
	if subfileVersion >= 10:
		furVectorsOffset = readAndParseIntBig(f,4)
		furLayersOffset = readAndParseIntBig(f,4)
	materialsOffset = readAndParseIntBig(f,4)
	tevsOffset = readAndParseIntBig(f,4)
	meshesOffset = readAndParseIntBig(f,4)
	textureLinksOffset = readAndParseIntBig(f,4)
	paletteLinksOffset = readAndParseIntBig(f,4)
	if subfileVersion >= 11:
		userDataOffset = readAndParseIntBig(f,4)
	nameOffset = readAndParseIntBig(f,4)
	name = read_brres_str(f,nameOffset,subfileOffset)
	
	modelHeaderCrumb = f.tell()
	modelHeaderSize = readAndParseIntBig(f,4)
	if modelHeaderSize != 0x40:
		print_warning(name+" doesn't have a modelHeaderSize of 0x40 (undefined behaviour)")
	modelHeaderOffset = readAndParseIntBig(f,4,signed=True)
	scalingMode = readAndParseIntBig(f,4)
	textureMatrixMode = readAndParseIntBig(f,4)
	vertexCount = readAndParseIntBig(f,4)
	faceCount = readAndParseIntBig(f,4)
	pathOffset = readAndParseIntBig(f,4)
	boneCount = readAndParseIntBig(f,4)
	useNormalMatrixArray = readAndParseIntBig(f,1)
	useTextureMatrixArray = readAndParseIntBig(f,1)
	useExtents = readAndParseIntBig(f,1)
	envelopeMatrixMode = readAndParseIntBig(f,1)
	weightLinkTableOffset = readAndParseIntBig(f,4)
	boundingBoxMin = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
	boundingBoxMax = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
	
	# many things use this instead of "raw" bone IDs
	# the general order is: single-bone weights, multi-bone weights (always -1), non-geometry bone IDs
	weightLinkTable = []
	if weightLinkTableOffset > 0:
		f.seek(weightLinkTableOffset+modelHeaderCrumb)
		weightLinkCount = readAndParseIntBig(f,4)
		for bl in range(weightLinkCount):
			weightLinkTable.append(readAndParseIntBig(f,4,signed=True))
	
	# the following will be two lists in one: single-bone weights, and multi-bone weights
	# it will be flattened into a single weight index list later
	weightsList = [[],[]]
	
	if furVectorsOffset > 0:
		print_warning(name+" has fur vectors, which aren't supported yet (skipping)")
	if furLayersOffset > 0:
		print_warning(name+" has fur layers, which aren't supported yet (skipping)")
	if tevsOffset > 0:
		print_warning(name+" has TEVs, which aren't supported yet (skipping)")
	if userDataOffset > 0:
		print_warning(name+" has userdata, which aren't supported yet (skipping)")
	
	defsMultiWeightGroups = {}
	defsMeshDraw = {}
	if definitionsOffset > 0:
		f.seek(definitionsOffset+subfileOffset)
		defsDict = parse_brres_dict(f)
		for d,(defName,defDataOffset) in enumerate(defsDict.items()):
			f.seek(defDataOffset)
			# fun with bytecode
			data = []
			while True:
				cmd = readAndParseIntBig(f,1)
				if cmd == 0x00: # no-op
					pass
				elif cmd == 0x01: # end signal
					break
				elif cmd == 0x02: # "node mapping" (implied to be bone-related but doesn't seem to be necessary)
					boneIndex = readAndParseIntBig(f,2)
					parentMatrixIndex = readAndParseIntBig(f,2)
					data.append([2,[boneIndex,parentMatrixIndex]])
				elif cmd == 0x03: # weighting
					weightID = readAndParseIntBig(f,2)
					weightCount = readAndParseIntBig(f,1)
					weights = []
					for w in range(weightCount):
						weightTableID = readAndParseIntBig(f,2)
						weightValue = readAndParseFloatBig(f)
						weights.append([weightLinkTable[weightTableID],weightValue])
					# currently the data is in [[i,v],[i,v]] format
					# this needs to be transposed into [[i,i],[v,v]] format
					weights = [list(x) for x in zip(*weights)]
					data.append([3,[weightID,weightCount,weights]])
					defsMultiWeightGroups[weightID] = weights
				elif cmd == 0x04: # mesh
					materialIndex = readAndParseIntBig(f,2)
					meshIndex = readAndParseIntBig(f,2)
					boneIndex = readAndParseIntBig(f,2)
					priority = readAndParseIntBig(f,1)
					defsMeshDraw[meshIndex] = [materialIndex,boneIndex,priority]
				elif cmd == 0x05: # "indexing"
					matrixID = readAndParseIntBig(f,2)
					weightIndex = readAndParseIntBig(f,2)
					data.append([5,[matrixID,weightIndex]])
				elif cmd == 0x06: # "duplicate matrix"
					toMatrix = readAndParseIntBig(f,2)
					fromMatrix = readAndParseIntBig(f,2)
					data.append([6,[toMatrix,fromMatrix]])
			#print("defData",data)
	# we can build the second part of the weights list now
	# we have to put in a lot of blank space so the list indexes align with the dict ones
	if defsMultiWeightGroups:
		for k in range(max(defsMultiWeightGroups.keys())+1):
			try:
				weightsList[1].append(defsMultiWeightGroups[k])
			except KeyError:
				weightsList[1].append([])
	
	# we do these link sections first because they might be useful later
	# dunno how to actually use them yet, though
	textureLinks = {}
	if textureLinksOffset > 0:
		f.seek(textureLinksOffset+subfileOffset)
		texLinkDict = parse_brres_dict(f)
		for b,(texLinkName,texLinkDataOffset) in enumerate(texLinkDict.items()):
			f.seek(texLinkDataOffset)
			texLinkCount = readAndParseIntBig(f,4)
			for tl in range(texLinkCount):
				textureLinks[texLinkName] = [readAndParseIntBig(f,4),readAndParseIntBig(f,4)]
	
	paletteLinks = {}
	if paletteLinksOffset > 0:
		f.seek(paletteLinksOffset+subfileOffset)
		palLinkDict = parse_brres_dict(f)
		for b,(palLinkName,palLinkDataOffset) in enumerate(palLinkDict.items()):
			f.seek(palLinkDataOffset)
			palLinkCount = readAndParseIntBig(f,4)
			for pl in range(palLinkCount):
				paletteLinks[palLinkName] = [readAndParseIntBig(f,4),readAndParseIntBig(f,4)]
	
	boneList = []
	boneLinkTable = {} # for turning bone indexes into link IDs
	if bonesOffset > 0:
		f.seek(bonesOffset+subfileOffset)
		boneDict = parse_brres_dict(f)
		for b,(boneName,boneDataOffset) in enumerate(boneDict.items()):
			f.seek(boneDataOffset)
			boneSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			boneNameOffset = readAndParseIntBig(f,4) # shouldn't need, already have name
			boneIndex = readAndParseIntBig(f,4)
			boneLinkID = readAndParseIntBig(f,4)
			boneLinkTable[boneIndex] = boneLinkID
			boneFlags = readAndParseIntBig(f,4)
			boneBillboardFormat = readAndParseIntBig(f,4)
			boneBillboardReference = readAndParseIntBig(f,4)
			boneScale = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			boneRot = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			bonePos = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			boneMin = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			boneMax = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			boneParentOffset = readAndParseIntBig(f,4,signed=True)
			boneFirstChildOffset = readAndParseIntBig(f,4,signed=True)
			boneNextSiblingOffset = readAndParseIntBig(f,4,signed=True)
			bonePrevSiblingOffset = readAndParseIntBig(f,4,signed=True)
			boneUserDataOffset = readAndParseIntBig(f,4,signed=True)
			# don't need this, but could come in handy maybe
			boneMatrix = mathutils.Matrix([
							[readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)],
							[readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)],
							[readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)],
							[0,0,0,1],
							])
			# definitely don't need the inverse matrix
			if boneParentOffset == 0:
				parentIndex = -1
			else: # have to travel to the parent bone and get its index
				f.seek(boneDataOffset+boneParentOffset+4*3)
				parentIndex = readAndParseIntBig(f,4)
			newBone = MonadoForgeBone(boneIndex)
			newBone.name = boneName
			newBone.parent = parentIndex
			newBone.position = bonePos+[1.0]
			newBone.rotation = mathutils.Euler([math.radians(d) for d in boneRot],"XYZ").to_quaternion()
			newBone.scale = boneScale+[1.0]
			boneList.append(newBone)
		# fill in the weight list with a bunch of 1.0 influence on every bone (to be used for single-bone verts)
		weightsList[0] = [[[x],[1.0]] for x in range(len(boneList))]
	
	# now that we have all the bones, we can calculate their global matrixes (they start with just local)
	globalBoneMatrixes = calculateGlobalBoneMatrixes(boneList)
	
	# now that we have the bone info, we can create the whole rest of the weights list
	multiWeightShiftIndex = len(weightsList[0])
	fullWeightIndexesList = weightsList[0]+weightsList[1] # no need to call flattened_list, it's simple enough
	
	# could call these "vertex tables" or just "vertices", doesn't matter too much
	positions = {}
	if positionsOffset > 0:
		f.seek(positionsOffset+subfileOffset)
		positionsDict = parse_brres_dict(f)
		for p,(positionName,positionDataOffset) in enumerate(positionsDict.items()):
			f.seek(positionDataOffset)
			positionSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			dataOffset = readAndParseIntBig(f,4)
			positionNameOffset = readAndParseIntBig(f,4) # probably not needed, already have a name
			positionIndex = readAndParseIntBig(f,4)
			positionDimensionality = readAndParseIntBig(f,4) # 0 = 2D, 1 = 3D
			positionDataFormat = readAndParseIntBig(f,4) # 0 = u8, 1 = i8, 2 = u16, 3 = i16, 4 = float
			positionNonFloatDivisor = readAndParseIntBig(f,1) # if not float, divide all positions by (1 << this)
			positionStrideSize = readAndParseIntBig(f,1) # only needed to keep place given unknowns
			positionVertexCount = readAndParseIntBig(f,2)
			positionBoundingBoxMin = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			positionBoundingBoxMax = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			f.seek(dataOffset+positionDataOffset)
			positions[positionIndex] = []
			for i in range(positionVertexCount):
				is3D = positionDimensionality == 1 # will be assigning Z = 0 for 2D positions
				divisor = 1 << positionNonFloatDivisor
				if positionDataFormat == 4:
					positions[positionIndex].append([readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f) if is3D else 0.0])
				elif positionDataFormat >= 0 and positionDataFormat <= 3:
					formatSize = [1,1,2,2][positionDataFormat]
					formatSigned = [False,True,False,True][positionDataFormat]
					positions[positionIndex].append([
														readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor,
														readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor,
														readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor if is3D else 0.0,
													])
				else:
					print_warning("unknown position data format: "+str(positionDataFormat))
					positions[positionIndex].append([0,0,0]) # need something so indices still line up
					f.seek(f.tell()+positionStrideSize)
	
	normals = {}
	if normalsOffset > 0:
		f.seek(normalsOffset+subfileOffset)
		normalsDict = parse_brres_dict(f)
		for p,(normalName,normalDataOffset) in enumerate(normalsDict.items()):
			f.seek(normalDataOffset)
			normalSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			dataOffset = readAndParseIntBig(f,4)
			normalNameOffset = readAndParseIntBig(f,4) # probably not needed, already have a name
			normalIndex = readAndParseIntBig(f,4)
			normalType = readAndParseIntBig(f,4) # 0 = normal, 1 = normal+binormal+tangent, 2 = normal or binormal or tangent
			if normalType != 0:
				print_warning("normalType is "+str(normalType)+"; this is not currently understood so results may be weird")
			normalDataFormat = readAndParseIntBig(f,4) # 0 = u8, 1 = i8, 2 = u16, 3 = i16, 4 = float
			normalNonFloatDivisor = readAndParseIntBig(f,1) # if not float, divide all normals by (1 << this)
			normalStrideSize = readAndParseIntBig(f,1) # only needed to keep place given unknowns
			normalCount = readAndParseIntBig(f,2)
			f.seek(dataOffset+normalDataOffset)
			normals[normalIndex] = []
			for i in range(normalCount):
				divisor = 1 << normalNonFloatDivisor
				if normalDataFormat == 4:
					normals[normalIndex].append([readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)])
				elif normalDataFormat >= 0 and normalDataFormat <= 3:
					formatSize = [1,1,2,2][normalDataFormat]
					formatSigned = [False,True,False,True][normalDataFormat]
					normals[normalIndex].append([
													readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor,
													readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor,
													readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor,
												])
				else:
					print_warning("unknown normal data format: "+str(normalDataFormat))
					normals[normalIndex].append([0,0,1]) # need something so indices still line up
					f.seek(f.tell()+normalStrideSize)
	
	# all colours will be represented with alpha just to make things easier (Blender also prefers it)
	colours = {}
	if coloursOffset > 0:
		f.seek(coloursOffset+subfileOffset)
		coloursDict = parse_brres_dict(f)
		for c,(colourName,colourDataOffset) in enumerate(coloursDict.items()):
			f.seek(colourDataOffset)
			colourSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			dataOffset = readAndParseIntBig(f,4)
			colourNameOffset = readAndParseIntBig(f,4) # probably not needed, already have a name
			colourIndex = readAndParseIntBig(f,4)
			colourHasAlpha = readAndParseIntBig(f,4) # 0 = RGB, 1 = RGBA
			colourDataFormat = readAndParseIntBig(f,4) # 0 = RGB565, 1 = RGB8, 2 = RGBX8, 3 = RGBA4, 4 = RGBA6, 5 = RGBA8
			colourStrideSize = readAndParseIntBig(f,1) # only needed to keep place given unknowns
			colourPadding = readAndParseIntBig(f,1)
			colourCount = readAndParseIntBig(f,2)
			colours[colourIndex] = []
			for i in range(colourCount):
				if colourDataFormat == 0: # RGB565
					data = readAndParseIntBig(f,2)
					colours[colourIndex].append([
						((data & 0b1111100000000000) >> 11)/31*255,
						((data & 0b0000011111100000) >> 5)/63*255,
						(data & 0b0000000000011111)/31*255,
						255])
				elif colourDataFormat == 1: # RGB8
					colours[colourIndex].append([readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1),255])
				elif colourDataFormat == 2: # RGBX8
					colours[colourIndex].append([readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1),255])
					unused = readAndParseIntBig(f,1) # sheesh what a dumb format that's 25% of your space completely wasted
				elif colourDataFormat == 3: # RGBA4
					data = readAndParseIntBig(f,2)
					colours[colourIndex].append([
						((data & 0xf000) >> 12)/15*255,
						((data & 0x0f00) >> 8)/15*255,
						((data & 0x00f0) >> 4)/15*255,
						( data & 0x000f)/15*255,
						])
				elif colourDataFormat == 4: # RGBA6
					params = f.read(3)
					bits = BitReader(params)
					colours[colourIndex].append([
						(bits.readbits(6))/63*255,
						(bits.readbits(6))/63*255,
						(bits.readbits(6))/63*255,
						(bits.readbits(6))/63*255,
						])
				elif colourDataFormat == 5: # RGBA8
					colours[colourIndex].append([readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1)])
				else:
					print_warning("unknown colour data format: "+str(colourDataFormat))
					colours[colourIndex].append([1.0,1.0,1.0,1.0]) # need something so indices still line up
					f.seek(f.tell()+colourStrideSize)
	
	uvs = {}
	if uvsOffset > 0:
		f.seek(uvsOffset+subfileOffset)
		uvsDict = parse_brres_dict(f)
		for uv,(uvName,uvDataOffset) in enumerate(uvsDict.items()):
			f.seek(uvDataOffset)
			uvSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			dataOffset = readAndParseIntBig(f,4)
			uvNameOffset = readAndParseIntBig(f,4) # probably not needed, already have a name
			uvIndex = readAndParseIntBig(f,4)
			uvDimensionality = readAndParseIntBig(f,4) # 0 = 1D, 1 = 2D
			uvDataFormat = readAndParseIntBig(f,4) # 0 = u8, 1 = i8, 2 = u16, 3 = i16, 4 = float
			uvNonFloatDivisor = readAndParseIntBig(f,1) # if not float, divide all positions by (1 << this)
			uvStrideSize = readAndParseIntBig(f,1) # only needed to keep place given unknowns
			uvCount = readAndParseIntBig(f,2)
			uvBoundingBoxMin = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			uvBoundingBoxMax = [readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)]
			f.seek(dataOffset+uvDataOffset)
			uvs[uvIndex] = []
			for i in range(uvCount): # reminder: the vertical must be inverted for all of these
				is2D = uvDimensionality == 1 # will be assigning V = 0 for 1D positions
				divisor = 1 << uvNonFloatDivisor
				if uvDataFormat == 4:
					uvs[uvIndex].append([readAndParseFloatBig(f),1.0-(readAndParseFloatBig(f) if is2D else 0.0)])
				elif uvDataFormat >= 0 and uvDataFormat <= 3:
					formatSize = [1,1,2,2][uvDataFormat]
					formatSigned = [False,True,False,True][uvDataFormat]
					uvs[uvIndex].append([
											readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor,
											1.0-(readAndParseIntBig(f,formatSize,signed=formatSigned)/divisor if is2D else 0.0),
										])
				else:
					print_warning("unknown uv data format: "+str(uvDataFormat))
					uvs[uvIndex].append([0,0]) # need something so indices still line up
					f.seek(f.tell()+uvStrideSize)
	
	# materials come next in the order, but we do them later so we can pass the colour/uv layer count
	# we can get away with this because the defs contain the mesh/material linking purely by index
	
	# these are called "objects" in BrawlBox and similar programs, but "meshes" makes more sense honestly
	meshes = {}
	maxColourLayers = 0
	maxUVLayers = 0
	if meshesOffset > 0: # a safe bet, but
		f.seek(meshesOffset+subfileOffset)
		meshDict = parse_brres_dict(f)
		for m,(meshName,meshDataOffset) in enumerate(meshDict.items()):
			f.seek(meshDataOffset)
			meshSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			singleBoneWeightIndex = readAndParseIntBig(f,4,signed=True) # -1 means multiple bones
			f.seek(meshDataOffset+0x30) # skip some unknowns/stuff this importer shouldn't need to know (hopefully!)
			featureFlags = readAndParseIntBig(f,4) # no idea which we need, so might as well set them all up
			flagPosMatrix = featureFlags & (1 << 0)
			flagTexMatrixes = [0,0,0,0,0,0,0,0]
			for i in range(8):
				flagTexMatrixes[i] = featureFlags & (1 << (i+1))
			flagPosition = featureFlags & (1 << 9)
			flagNormal = featureFlags & (1 << 10)
			flagColours = [0,0]
			for i in range(2):
				flagColours[i] = featureFlags & (1 << (i+11))
			flagUVs = [0,0,0,0,0,0,0,0]
			for i in range(8):
				flagUVs[i] = featureFlags & (1 << (i+13))
			meshFlags = readAndParseIntBig(f,4)
			flagInvisible = meshFlags & (1 << 0)
			flagChangeCurrentMatrix = meshFlags & (1 << 1)
			meshNameOffset = readAndParseIntBig(f,4) # probably not needed, already have a name
			meshIndex = readAndParseIntBig(f,4)
			meshVertexCount = readAndParseIntBig(f,4)
			meshFaceCount = readAndParseIntBig(f,4)
			meshVerticesIndex = readAndParseIntBig(f,2,signed=True)
			meshNormalsIndex = readAndParseIntBig(f,2,signed=True)
			meshColourIndexes = [-1,-1]
			currentColourLayers = 0
			for i in range(2):
				meshColourIndexes[i] = readAndParseIntBig(f,2,signed=True)
				if meshColourIndexes[i] != -1:
					currentColourLayers += 1
			maxColourLayers = max(currentColourLayers,maxColourLayers)
			meshUVIndexes = [-1,-1,-1,-1,-1,-1,-1,-1]
			currentUVLayers = 0
			for i in range(8):
				meshUVIndexes[i] = readAndParseIntBig(f,2,signed=True)
				if meshUVIndexes[i] != -1:
					currentUVLayers += 1
			maxUVLayers = max(currentUVLayers,maxUVLayers)
			if subfileVersion >= 10:
				meshFurVectorsIndex = readAndParseIntBig(f,2,signed=True)
				meshFurLayersIndex = readAndParseIntBig(f,2,signed=True)
			weightIndexTableOffset = readAndParseIntBig(f,4,signed=True)
			f.seek(weightIndexTableOffset+meshDataOffset)
			weightIndexTableCount = readAndParseIntBig(f,4)
			weightIndexTableData = []
			for weightItem in range(weightIndexTableCount):
				weightIndexTableData.append(readAndParseIntBig(f,2))
			# this is now raw Wii graphics code (ugliness guaranteed)
			# the deal is: some commands define the format, and then other commands read the data in said format
			# the basic pattern is defining the bit-size of indexes with 0850 and 0860 cmds
			# for one-bit flags, 0 = not present and 1 = present as an 8-bit index
			# for two-bit flags: 00 = not present, 10 = 8-bit, 11 = 16-bit; 01 = data is directly in the params instead of being indexed
			# in the "direct" case, further commands (0870, 0880, 0890) define the format of the data
			flagPatterns = {
							"0850":[1,1,1,1,1,1,1,1,1,2,2,2,2,15], # posMat, texMat0-7, pos, nrm, col0, col1, unused*15
							"0860":[2,2,2,2,2,2,2,2,16], # tex0-7, unused*16
							"0870":[1,3,5,1,3,1,3,1,3,1,3,5,1,1], # posE, posFrm, posDiv, nrmE, nrmFrm, col0E, col0Frm, col1E, col1Frm, tex0E, tex0Frm, tex0Div, dequant, Nrm3
							"0880":[1,3,5,1,3,5,1,3,5,1,3,1], # tex1E, tex1Frm, tex1Div, tex2E, tex2Frm, tex2Div, tex3E, tex3Frm, tex3Div, tex4E, tex4Frm, unused*1
							"0890":[5,1,3,5,1,3,5,1,3,5], # tex4Div, tex5E, tex5Frm, tex5Div, tex6E, tex6Frm, tex6Div, tex7E, tex7Frm, tex7Div
							"101008":[2,2,4,24], # colNum, nrmNum, texCrdNum, unused*24
							"10104x":[1,1,1,1,3,5,3,3,14], # ?, projection, input form, ?, tex gen type, source row, texcoord, light index, unused*14
							# there's more, but they're for materials rather than geometry, going to presume we don't need them for now
							}
			indexWidths = flagPatterns["0850"][0:-1]+flagPatterns["0860"][0:-1]
			# the following use magic numbers because they leave out the unused items
			combinedCPIndexedFlags = [0]*(13+8)
			combinedCPEmbeddedFlags = [0]*(14+11+10)
			unknownCmds = []
			# there will be a lot of duplicate vertices, that's fine for now
			forgeVerts = MonadoForgeVertexList()
			forgeFaces = []
			hashedVertsByPosition = {} # this is for faster duplicate culling later
			curVIndex = 0
			# the following are volatile arrays: they will be overwritten with new stuff constantly
			# this is why we can't just bulk all the vertices at once, they need the most recently-loaded index set
			# they're not actually arrays because we can just use the memory address target as a dict key (nice and simple)
			indexedMatrixesPos = {}
			indexedMatrixesNrm = {}
			indexedMatrixesTex = {}
			indexedMatrixesLgt = {}
			try: # this try is primarily so we can still print unknownCmds if something goes wrong
				while f.tell() < meshSize+meshDataOffset:
					faces = []
					cmd = readAndParseIntBig(f,1)
					if cmd == 0x00: # no-op
						pass
					elif cmd == 0x08: # load CP
						subcmd = readAndParseIntBig(f,1)
						params = f.read(4)
						bits = BitReader(params)
						readFields = []
						# the flag patterns are reversed (and then unreversed via [::-1] after being read so the unused are skipped)
						# because they're in little-first order but we kinda have to read in big-first order
						if subcmd == 0x50:
							for p in reversed(flagPatterns["0850"]):
								readFields.append(bits.readbits(p))
							combinedCPIndexedFlags[0:13] = readFields[13:0:-1]
						elif subcmd == 0x60:
							for p in reversed(flagPatterns["0860"]):
								readFields.append(bits.readbits(p))
							combinedCPIndexedFlags[13:21] = readFields[8:0:-1]
						elif subcmd == 0x70:
							for p in reversed(flagPatterns["0870"]):
								readFields.append(bits.readbits(p))
							combinedCPEmbeddedFlags[0:14] = readFields[14:0:-1]
						elif subcmd == 0x80:
							for p in reversed(flagPatterns["0880"]):
								readFields.append(bits.readbits(p))
							combinedCPEmbeddedFlags[14:25] = readFields[11:0:-1]
						elif subcmd == 0x90:
							for p in reversed(flagPatterns["0890"]):
								readFields.append(bits.readbits(p))
							combinedCPEmbeddedFlags[25:35] = readFields[10:0:-1]
					elif cmd == 0x10: # load XF
						# don't know how much we need this yet, so only kinda roughing it in
						transferSize = readAndParseIntBig(f,2) + 1
						address = readAndParseIntBig(f,2)
						params = f.read(4)
						bits = BitReader(params)
						# reminder: have to read things in backwards
						if address == 0x1008:
							unused = bits.readbits(24)
							texCoordCount = bits.readbits(4)
							normalCount = bits.readbits(2)
							colourCount = bits.readbits(2)
						#elif address == 0x1040 # uhhh not yet sure how to deal with the 4th digit also being a value (hopefully don't need it)
					# okay according to the BrawlBox code some of this stuff is:
					# 16 bits of index
					# 4 bits of "length-1" (says you have to add 1 to get the true value)
					# 8 bits of memory address (needed to know what's being replaced from the current array)
					elif cmd == 0x20: # indexed 4x3 position matrix (...what does that mean exactly?)
						mtxIndex = readAndParseIntBig(f,2)
						otherStuff = readAndParseIntBig(f,2)
						chunkLength = (otherStuff >> 12)+1
						memAddr = otherStuff & 0xff
						indexedMatrixesPos[memAddr//chunkLength] = mtxIndex
					elif cmd == 0x28: # indexed 3x3 normal matrix (same as above)
						mtxIndex = readAndParseIntBig(f,2)
						otherStuff = readAndParseIntBig(f,2)
						chunkLength = (otherStuff >> 12)+1
						memAddr = otherStuff & 0xff
						indexedMatrixesNrm[memAddr//chunkLength] = mtxIndex
					elif cmd == 0x30: # indexed 4x4 texture matrix (same as above)
						mtxIndex = readAndParseIntBig(f,2)
						otherStuff = readAndParseIntBig(f,2)
						chunkLength = (otherStuff >> 12)+1
						memAddr = otherStuff & 0xff
						indexedMatrixesTex[memAddr//chunkLength] = mtxIndex
					elif cmd == 0x38: # light-based something or other???
						mtxIndex = readAndParseIntBig(f,2)
						otherStuff = readAndParseIntBig(f,2)
						chunkLength = (otherStuff >> 12)+1
						memAddr = otherStuff & 0xff
						indexedMatrixesLgt[memAddr//chunkLength] = mtxIndex
					# draw commands not put in yet: 0x80 quads, 0xa0 tri-fan, 0xa8 lines, 0xb0 line-strip, 0xb8 points
					elif cmd == 0x90 or cmd == 0x98: # draw commands
						vertCount = readAndParseIntBig(f,2)
						vertData = []
						for i in range(vertCount):
							vert = []
							for j,v in enumerate(indexWidths):
								vert.append(-1) # add a null, then replace it with what's read
								if v == 1:
									if combinedCPIndexedFlags[j] == 0:
										pass # not present
									elif combinedCPIndexedFlags[j] == 1:
										vert[-1] = readAndParseIntBig(f,1)
									else:
										print_warning("unsupported situation found @ "+str(f.tell()))
								elif v == 2:
									if combinedCPIndexedFlags[j] == 0:
										pass # not present
									elif combinedCPIndexedFlags[j] == 1:
										print_warning("direct embedded draw cmds not currently supported @ "+str(f.tell()))
									elif combinedCPIndexedFlags[j] == 2:
										vert[-1] = readAndParseIntBig(f,1)
									elif combinedCPIndexedFlags[j] == 3:
										vert[-1] = readAndParseIntBig(f,2)
									else:
										print_warning("unsupported situation found @ "+str(f.tell()))
							vertData.append(vert)
						if cmd == 0x90: # triangles
							for v in range(0,len(vertData),3):
								# the vert order is backwards (2,1,0) for normals purposes
								faces.append([vertData[v+2],vertData[v+1],vertData[v]])
						if cmd == 0x98: # triangle strip
							for v in range(len(vertData)-2):
								# if we just add the verts in order, the strip will keep alternating between clockwise and CCW
								# so we have to invert the direction of every other face
								if v % 2 == 0:
									faces.append([vertData[v+2],vertData[v+1],vertData[v]])
								else:
									faces.append([vertData[v],vertData[v+1],vertData[v+2]])
					else: # all options exhausted, not a known/supported code
						if cmd not in unknownCmds: unknownCmds.append(cmd)
					for face in faces:
						faceVerts = []
						newFaceIndex = len(forgeFaces)
						for vert in face:
							newVertex = MonadoForgeVertex(curVIndex)
							if vert[9] != -1: # should never happen (a vertex without position), but
								pos = positions[meshVerticesIndex][vert[9]]
								if vert[10] != -1: # normal
									nrm = normals[meshNormalsIndex][vert[10]]
								singleBone = None
								boneListIndex = -1
								if singleBoneWeightIndex != -1: # entire mesh uses the same bone
									boneListIndexTarget = singleBoneWeightIndex
								else: # per-vertex weights
									# but what if vert[0] is -1? apparently that's a thing
									boneListIndexTarget = indexedMatrixesPos[vert[0]//3]
								boneListIndex = weightLinkTable[boneListIndexTarget]
								newVertex.weightSetIndex = boneListIndex
								if boneListIndex == -1: # not a single bone vertex
									newVertex.weightSetIndex = boneListIndexTarget+multiWeightShiftIndex
								else: # is a single bone vertex
									# these vertices are origin-clustered and modified into position based on their bone
									singleBone = boneList[boneListIndex]
									boneMatrix = globalBoneMatrixes[boneListIndex]
									pos = boneMatrix @ mathutils.Vector(pos)
									if vert[10] != -1:
										# rotation part only
										nrmMatrix = boneMatrix.to_quaternion().to_matrix()
										nrm = nrmMatrix @ mathutils.Vector(nrm)
								newVertex.position = pos
								if vert[10] != -1: # normal
									newVertex.normal = nrm
							else:
								print_warning("vertex without position: "+str(vert))
							if vert[11] != -1: # colour 1
								newVertex.setColour(0,colours[meshColourIndexes[0]][vert[11]])
							if vert[12] != -1: # colour 2
								newVertex.setColour(1,colours[meshColourIndexes[1]][vert[12]])
							for uvLayer,uvIndex in enumerate(vert[13:21]):
								uvMatrixIndex = vert[uvLayer+1] # vert[1] - vert[8]
								if uvMatrixIndex != -1: # don't know what to do here yet
									print_warning("uvMatrixIndex == "+str(uvMatrixIndex))
								if uvIndex != -1:
									newVertex.setUV(uvLayer,uvs[meshUVIndexes[uvLayer]][uvIndex])
							forgeVerts.addVertex(curVIndex,newVertex,automerge=True)
							faceVerts.append(curVIndex)
							curVIndex += 1
						newFace = MonadoForgeFace(newFaceIndex)
						newFace.vertexIndexes = faceVerts
						forgeFaces.append(newFace)
			finally:
				if unknownCmds:
					print_warning("found unknown graphic commands: "+", ".join(hex(x) for x in unknownCmds))
			newMesh = MonadoForgeMesh()
			newMesh.name = name+"_"+meshName
			newMesh.vertices = forgeVerts
			newMesh.faces = forgeFaces
			newMesh.materialIndex = defsMeshDraw[meshIndex][0]
			newMesh.weightSets = fullWeightIndexesList
			meshes[m] = newMesh
	
	materials = {}
	if materialsOffset > 0:
		f.seek(materialsOffset+subfileOffset)
		materialsDict = parse_brres_dict(f)
		for material,(materialName,materialDataOffset) in enumerate(materialsDict.items()):
			f.seek(materialDataOffset)
			materialSize = readAndParseIntBig(f,4)
			parentSubfileOffset = readAndParseIntBig(f,4,signed=True)
			#dataOffset = readAndParseIntBig(f,4)
			materialNameOffset = readAndParseIntBig(f,4) # probably not needed, already have a name
			materialIndex = readAndParseIntBig(f,4)
			# probably don't need most of these, but might as well set them up just in case
			materialFlags = readAndParseIntBig(f,4)
			flagIsXLU = (materialFlags & 0x80000000) != 0 # specifically, has alpha aside from 1.0 or 0.0
			flagNoTexMatrix = (materialFlags & 0x00000080) != 0
			flagNoTexCoords = (materialFlags & 0x00000040) != 0
			flagNoGenMode = (materialFlags & 0x00000020) != 0
			flagNoLighting = (materialFlags & 0x00000010) != 0
			flagNoIndirectMatrix = (materialFlags & 0x00000008) != 0
			flagNoTexCoordScale = (materialFlags & 0x00000004) != 0
			flagNoTEVColour = (materialFlags & 0x00000002) != 0
			flagNoPixelDisplay = (materialFlags & 0x00000001) != 0
			materialTexgenCount = readAndParseIntBig(f,1)
			materialLightChannelCount = readAndParseIntBig(f,1)
			materialShaderStageCount = readAndParseIntBig(f,1)
			materialIndirectTexCount = readAndParseIntBig(f,1)
			materialCulling = readAndParseIntBig(f,4) # bitflags: 1 = cull front, 2 = cull back
			materialDepthTesting = readAndParseIntBig(f,1)
			materialLightsetIndex = readAndParseIntBig(f,1)
			materialFogIndex = readAndParseIntBig(f,1)
			materialPadding = readAndParseIntBig(f,1)
			materialIndirectMethod = readAndParseIntBig(f,4)
			materialLightNrmMapRef = readAndParseIntBig(f,4)
			materialShaderOffset = readAndParseIntBig(f,4,signed=True)
			materialTexCount = readAndParseIntBig(f,4)
			materialLayerOffset = readAndParseIntBig(f,4,signed=True)
			materialOtherOffset1 = readAndParseIntBig(f,4,signed=True) # these change based on version and don't seem needed for XC1, so not trying too hard
			materialOtherOffset2 = readAndParseIntBig(f,4,signed=True)
			materialOtherOffset3 = readAndParseIntBig(f,4,signed=True)
			materialTexMapUsage = readAndParseIntBig(f,4) # flags for which texture maps are used
			f.seek(f.tell()+0x100) # "Precompiled code space containing texture information."
			materialPaletteUsage = readAndParseIntBig(f,4) # flags for which palettes are used
			f.seek(f.tell()+0x60) # "Precompiled code space containing palette information."
			materialFixFlags = readAndParseIntBig(f,4) # bitflags: 1 = enable layer, 2 = fixed scale, 4 = fixed rotation, 8 = fixed translation
			materialTexMatrixMode = readAndParseIntBig(f,4) # 0 = "Maya", 1 = "XSI", 2 = "3DS Max" (what do any of these actually mean)
			materialCoordinates = []
			for i in range(8):
				scaleCoords = [readAndParseFloatBig(f),readAndParseFloatBig(f)]
				rotCoords = readAndParseFloatBig(f)
				transCoords = [readAndParseFloatBig(f),readAndParseFloatBig(f)]
				materialCoordinates.append([scaleCoords,rotCoords,transCoords])
			materialTexMatrixes = []
			for i in range(8):
				camRef = readAndParseIntBig(f,1,signed=True)
				lightRef = readAndParseIntBig(f,1,signed=True)
				mapMode = readAndParseIntBig(f,1) # 0 = UVs, 1 = camera, 2 = projection, 3 = list, 4 = specular
				identityEffect = readAndParseIntBig(f,1)
				texMatrix = [
								[readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)],
								[readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)],
								[readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f),readAndParseFloatBig(f)],
							]
				materialTexMatrixes = [camRef,lightRef,mapMode,identityEffect,texMatrix]
			materialLightChannels = []
			for i in range(8):
				lightFlags = readAndParseIntBig(f,4) # bitflags: 1 = material colour, 2 = material alpha, 4 = ambient colour, 8 = ambient alpha, 16 = raster colour, 32 = raster alpha
				baseMaterialColour = [readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1)] # RGBA
				baseAmbientColour = [readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1),readAndParseIntBig(f,1)] # RGBA
				colourChannelControl = readAndParseIntBig(f,4) # probably some other sort of flags
				alphaChannelControl = readAndParseIntBig(f,4) # same
				materialLightChannels.append([lightFlags,baseMaterialColour,baseAmbientColour,colourChannelControl,alphaChannelControl])
			f.seek(materialDataOffset+materialLayerOffset)
			textureData = []
			for t in range(materialTexCount):
				texNameOffset = readAndParseIntBig(f,4,signed=True)
				paletteNameOffset = readAndParseIntBig(f,4,signed=True)
				texDataOffset = readAndParseIntBig(f,4,signed=True) # unused/dummy?
				paletteDataOffset = readAndParseIntBig(f,4,signed=True) # unused/dummy?
				texDataID = readAndParseIntBig(f,4)
				paletteDataID = readAndParseIntBig(f,4)
				texWrapU = readAndParseIntBig(f,4) # 0 = clamp, 1 = repeat, 2 = mirror
				texWrapV = readAndParseIntBig(f,4)
				texFilterModeSmaller = readAndParseIntBig(f,4) # 0 = nearest, 1 = linear, 2 = nearest mipmap nearest, 3 = linear mipmap nearest, 4 = nearest mipmap linear, 5 = linear mipmap linear
				texFilterModeLarger = readAndParseIntBig(f,4) # 0 = nearest, 1 = linear
				texLODBias = readAndParseFloatBig(f)
				texMaxAnisotropy = readAndParseIntBig(f,4) # 0 = 1, 1 = 2, 2 = 4
				texClampBias = readAndParseIntBig(f,1)
				texTexelInterpolate = readAndParseIntBig(f,1)
				texPadding = readAndParseIntBig(f,2)
				textureName = read_brres_str(f,texNameOffset,materialDataOffset+materialLayerOffset+52*t) # the extra 52 is because of the reads in this for-loop
				textureData.append([textureName,texWrapU,texWrapV,texFilterModeLarger])
			# all the stuff is in now, process it
			newMat = MonadoForgeMaterial(materialIndex)
			newMat.name = materialName
			newMat.cullingFront = (materialCulling & 1) == 1
			newMat.cullingBack = ((materialCulling & 2)>>1) == 1
			newMat.transparency = 2 if flagIsXLU else 0 # alpha clip not yet detected
			newMat.colourLayerCount = maxColourLayers
			newMat.uvLayerCount = maxUVLayers
			for tex in textureData:
				newTex = MonadoForgeTexture()
				newTex.name = tex[0]
				uRepeat = tex[1] != 0 # not "== 1" because mirror also requires repeat
				vRepeat = tex[2] != 0
				uMirror = tex[1] == 2
				vMirror = tex[2] == 2
				newTex.repeating = [uRepeat,vRepeat]
				newTex.mirroring = [uMirror,vMirror]
				newTex.isFiltered = tex[3] == 1
				newMat.addTexture(newTex)
			materials[materialIndex] = newMat
	
	results = MonadoForgeImportedPackage()
	skel = MonadoForgeSkeleton()
	skel.bones = boneList
	results.skeleton = skel
	results.meshes = list(meshes.values())
	results.materials = list(materials.values())
	if printProgress:
		print("Finished parsing MDL0 from .brres file.")
	return results

def parse_plt0(f, context, subfileOffset):
	printProgress = context.scene.monado_forge_main.printProgress
	startBreadcrumb = f.tell()
	subfileLength = readAndParseIntBig(f,4)
	subfileVersion = readAndParseIntBig(f,4)
	subfileParentOffset = readAndParseIntBig(f,4,signed=True)
	
	pltHeaderCrumb = f.tell()
	pltHeaderSize = readAndParseIntBig(f,4)
	if pltHeaderSize != 0x40:
		print_warning("palette at "+str(subfileOffset)+" doesn't have a pltHeaderSize of 0x40 (undefined behaviour)")
	nameOffset = readAndParseIntBig(f,4)
	name = read_brres_str(f,nameOffset,subfileOffset)
	paletteFormat = readAndParseIntBig(f,4)
	colourCount = readAndParseIntBig(f,2)
	
	f.seek(pltHeaderSize+subfileOffset)
	colours = []
	# all these results are in 255 format
	if paletteFormat == 1: # RGB565
		for c in range(colourCount):
			data = readAndParseIntBig(f,2)
			r = ((data & 0b1111100000000000) >> 11)/31*255
			g = ((data & 0b0000011111100000) >> 5)/63*255
			b = (data & 0b0000000000011111)/31*255
			colours.append([r,g,b,255])
	elif paletteFormat == 2: # RGB5A3
		for c in range(colourCount):
			data = readAndParseIntBig(f,2)
			mode = (data & 0b1000000000000000) >> 15
			if mode:
				r = ((data & 0b0111110000000000) >> 10)/31*255
				g = ((data & 0b0000001111100000) >> 5)/31*255
				b = (data & 0b0000000000011111)/31*255
				colours.append([r,g,b,255])
			else:
				a = ((data & 0b0111000000000000) >> 12)/7*255
				r = ((data & 0b0000111100000000) >> 8)/15*255
				g = ((data & 0b0000000011110000) >> 4)/15*255
				b = (data & 0b0000000000001111)/15*255
				colours.append([r,g,b,a])
	else:
		print_error("PLT0 block "+name+"is of unknown/unsupported format "+str(paletteFormat))
	return name,colours

def parse_tex0(f, context, subfileOffset, palettesDict):
	printProgress = context.scene.monado_forge_main.printProgress
	texPath = None
	if context.scene.monado_forge_import.autoSaveTextures:
		texPath = bpy.path.abspath(context.scene.monado_forge_import.texturePath)
	startBreadcrumb = f.tell()
	subfileLength = readAndParseIntBig(f,4)
	subfileVersion = readAndParseIntBig(f,4)
	subfileParentOffset = readAndParseIntBig(f,4,signed=True)
	
	texHeaderCrumb = f.tell()
	texHeaderSize = readAndParseIntBig(f,4)
	if texHeaderSize != 0x40:
		print_warning("texture at "+str(subfileOffset)+" doesn't have a texHeaderSize of 0x40 (undefined behaviour)")
	nameOffset = readAndParseIntBig(f,4)
	name = read_brres_str(f,nameOffset,subfileOffset)
	ciFlag = readAndParseIntBig(f,4)
	imgWidth = readAndParseIntBig(f,2)
	imgHeight = readAndParseIntBig(f,2)
	imgFormat = readAndParseIntBig(f,4)
	mipmapCount = readAndParseIntBig(f,4)
	minMipmap = readAndParseFloatBig(f)
	maxMipmap = readAndParseFloatBig(f)
	unused = readAndParseIntBig(f,4)
	
	# assumption: texture name always matches palette name
	palette = palettesDict.get(name,[])
	
	f.seek(texHeaderSize+subfileOffset)
	# here is the raw image data
	imgName = parse_texture_brres(name,imgFormat,imgWidth,imgHeight,f.read(subfileLength-texHeaderSize),palette,printProgress,saveTo=texPath)

def import_brres_root(f, context):
	printProgress = context.scene.monado_forge_main.printProgress
	
	magic = f.read(4)
	if magic != b"bres":
		print_error(f.name+" is not a valid BRRES file (unexpected header)")
		return None
	bom = f.read(2)
	if bom != b"\xfe\xff":
		print_error(f.name+" doesn't have the big-endian BOM (not normal for XC1 files)")
		return None
	rootVersion = readAndParseIntBig(f,2)
	filesize = readAndParseIntBig(f,4) # seems to not include end padding (though the padding might be an artifact of the nameless XC1 file splitter)
	rootOffset = readAndParseIntBig(f,2)
	sectionCount = readAndParseIntBig(f,2)
	
	f.seek(rootOffset)
	rootMagic = f.read(4)
	if rootMagic != b"root":
		print_error(f.name+" is not a valid BRRES file (root is not named root)")
		return None
	rootSize = readAndParseIntBig(f,4)
	rootDict = parse_brres_dict(f)
	globalDict = {}
	# assumption: if two subfiles are in the same folder, they cannot share a name
	# they can share names if they're in different folders (e.g. 66077.brres oj010010)
	for rootFolder in rootDict.items():
		folderName,folderOffset = rootFolder
		f.seek(folderOffset)
		folderDict = parse_brres_dict(f,folderName+"/")
		globalDict.update(folderDict)
	results = {}
	for subfile in globalDict.items():
		subfileName,subfileOffset = subfile
		f.seek(subfileOffset)
		submagic = f.read(4)
		# there's a common format to the subfile headers, but it's more convenient to pretend otherwise
		# was going to set this up with some cleverness about a function map, but decided it was overcomplicating things
		if submagic == b"MDL0":
			if "MDL0" not in results.keys(): results["MDL0"] = []
			results["MDL0"].append(parse_mdl0(f,context,subfileOffset))
		elif submagic == b"PLT0":
			# assumption: palette names are never shared in a single .brres file
			if "PLT0" not in results.keys(): results["PLT0"] = {}
			pltName,pltColours = parse_plt0(f,context,subfileOffset)
			results["PLT0"][pltName] = pltColours
		elif submagic == b"TEX0":
			# textures are just imported straight to Blender, no passing of results needed
			# assumption: any necessary PLT0 file will always be imported first
			parse_tex0(f,context,subfileOffset,results.get("PLT0",{}))
		else:
			print_warning(str(submagic)+" files not yet supported, skipping")
	
	if len(results["MDL0"]) > 1:
		print_warning("found multiple MDL0s in this file, only processing the first for now")
	return results["MDL0"][0]

def import_brres(self, context):
	absoluteFilePath = bpy.path.abspath(context.scene.monado_forge_import.singlePath)
	if context.scene.monado_forge_main.printProgress:
		print("Importing from: "+absoluteFilePath)
	if os.path.splitext(absoluteFilePath)[1] != ".brres":
		self.report({"ERROR"}, "File was not a .brres file")
		return {"CANCELLED"}
	
	with open(absoluteFilePath, "rb") as f:
		brresResult = import_brres_root(f, context)
	
	return realise_results(brresResult, os.path.splitext(os.path.basename(absoluteFilePath))[0], self, context)

def register():
	pass

def unregister():
	pass

#[...]