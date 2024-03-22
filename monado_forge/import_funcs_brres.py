import bpy
import io
import math
import mathutils
import os

from . classes import *
from . utils import *
from . import_funcs import *
from . modify_funcs import *

# various sources:
# https://wiki.tockdom.com/wiki/BRRES_(File_Format)
# https://avsys.xyz/wiki/BRRES_(File_Format)
# the raw C++-masquerading-as-C# code of BrawlBox v0.66 (why else would it all be pointers >:( )

def read_brres_str(f,pointer,offset):
	crumb = f.tell()
	f.seek(offset+pointer - 4) # have to "back up" 4 to get the length (could just do a till-null read, but this is safer)
	length = readAndParseIntBig(f,4)
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
	
	if uvsOffset > 0:
		print_warning(name+" has UVs, which aren't supported yet (skipping)")
	if furVectorsOffset > 0:
		print_warning(name+" has fur vectors, which aren't supported yet (skipping)")
	if furLayersOffset > 0:
		print_warning(name+" has fur layers, which aren't supported yet (skipping)")
	if materialsOffset > 0:
		print_warning(name+" has materials, which aren't supported yet (skipping)")
	if tevsOffset > 0:
		print_warning(name+" has TEVs, which aren't supported yet (skipping)")
	if textureLinksOffset > 0:
		print_warning(name+" has texture links, which aren't supported yet (skipping)")
	if paletteLinksOffset > 0:
		print_warning(name+" has palette links, which aren't supported yet (skipping)")
	if userDataOffset > 0:
		print_warning(name+" has userdata, which aren't supported yet (skipping)")
	
	defsMultiWeightGroups = {}
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
					data.append([4,[meshIndex,materialIndex,boneIndex,priority]])
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
			newBone.setName(boneName)
			newBone.setParent(parentIndex)
			newBone.setPosition(bonePos+[1.0])
			newBone.setRotation(mathutils.Euler(boneRot,"XYZ").to_quaternion())
			newBone.setRotation(mathutils.Euler([math.radians(d) for d in boneRot],"XYZ").to_quaternion())
			newBone.setScale(boneScale+[1.0])
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
	
	# these are called "objects" in BrawlBox and similar programs, but "meshes" makes more sense honestly
	meshes = {}
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
			for i in range(2):
				meshColourIndexes[i] = readAndParseIntBig(f,2,signed=True)
			meshUVIndexes = [-1,-1,-1,-1,-1,-1,-1,-1]
			for i in range(8):
				meshUVIndexes[i] = readAndParseIntBig(f,2,signed=True)
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
			# for two-bit flags: 00 = not present, 10 = 8-bit, 11 = 16-bit; 10 = data is directly in the params instead of being indexed
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
			# we also have to index them manually (i.e. no calling .indexVertices() later)
			forgeVerts = []
			forgeFaces = []
			hashedVertsByPosition = {} # this is for faster duplicate culling later
			curVIndex = 0
			# the following are volatile arrays: they will be overwritten with new stuff constantly
			# this is why we can't just bulk all the vertices at once, they need the most recently-loaded index set
			# they're not actually arrays because we can just use the memory address target as a dict key (nice and simple)
			indexedMatrixesPos = {}
			indexedMatrixesNrm = {}
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
				# draw commands not put in yet: 0x80 quads, 0xa0 tri-fan, 0xa8 lines, 0xb0 line-strip, 0xb8 points
				elif cmd == 0x90 or cmd == 0x98: # draw commands
					vertCount = readAndParseIntBig(f,2)
					vertData = []
					for i in range(vertCount):
						vert = []
						for j,v in enumerate(indexWidths):
							vert.append(-1) # add a null, then replace it with what's read
							if v == 1 and combinedCPIndexedFlags[j] == 1:
								vert[-1] = readAndParseIntBig(f,1)
							elif v == 2:
								if combinedCPIndexedFlags[j] == 1:
									print_warning("direct embedded draw cmds not currently supported")
								elif combinedCPIndexedFlags[j] == 2:
									vert[-1] = readAndParseIntBig(f,1)
								elif combinedCPIndexedFlags[j] == 3:
									vert[-1] = readAndParseIntBig(f,2)
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
					for vert in face:
						newVertex = MonadoForgeVertex()
						newVertex._id = curVIndex
						if vert[9] != -1: # should never happen (a vertex without position), but
							pos = positions[meshVerticesIndex][vert[9]]
							if vert[10] != -1: # normal
								nrm = normals[meshNormalsIndex][vert[10]]
							singleBone = None
							boneListIndex = -1
							if singleBoneWeightIndex != -1: # entire mesh uses the same bone
								boneListIndexTarget = singleBoneWeightIndex
							else: # per-vertex weights
								boneListIndexTarget = indexedMatrixesPos[vert[0]//3]
							boneListIndex = weightLinkTable[boneListIndexTarget]
							newVertex.setWeightSetIndex(boneListIndex)
							if boneListIndex == -1: # not a single bone vertex
								newVertex.setWeightSetIndex(boneListIndexTarget+multiWeightShiftIndex)
							else: # is a single bone vertex
								# these vertices are origin-clustered and modified into position based on their bone
								singleBone = boneList[boneListIndex]
								boneMatrix = globalBoneMatrixes[boneListIndex]
								pos = boneMatrix @ mathutils.Vector(pos)
								if vert[10] != -1:
									# rotation part only
									nrmMatrix = boneMatrix.to_quaternion().to_matrix()
									nrm = nrmMatrix @ mathutils.Vector(nrm)
							newVertex.setPosition(pos)
							if vert[10] != -1: # normal
								newVertex.setNormal(nrm)
						if vert[11] != -1: # colour 1
							newVertex.setColour(0,colours[meshColourIndexes[0]][vert[11]])
						if vert[12] != -1: # colour 2
							newVertex.setColour(1,colours[meshColourIndexes[1]][vert[12]])
						# before adding this vertex, we must check for if it's a duplicate, and if so use the existing other instead
						# this would be very expensive without hashing the position
						foundDouble = False
						thisPosHashed = tuple(newVertex.getPosition())
						if thisPosHashed in hashedVertsByPosition.keys():
							other = hashedVertsByPosition[thisPosHashed]
							if newVertex.isDouble(other):
								faceVerts.append(other.getID())
								foundDouble = True
						if not foundDouble:
							forgeVerts.append(newVertex)
							faceVerts.append(curVIndex)
							hashedVertsByPosition[tuple(newVertex.getPosition())] = newVertex
							curVIndex += 1
					newFace = MonadoForgeFace()
					newFace.setVertexIndexes(faceVerts)
					forgeFaces.append(newFace)
			if unknownCmds:
				print_warning("found unknown graphic commands: "+", ".join(hex(x) for x in unknownCmds))
			newMesh = MonadoForgeMesh()
			newMesh.setName(name+"_"+meshName)
			newMesh.setVertices(forgeVerts)
			newMesh.setFaces(forgeFaces)
			newMesh.setWeightSets(fullWeightIndexesList)
			meshes[m] = newMesh
	
	results = MonadoForgeImportedPackage()
	skel = MonadoForgeSkeleton()
	skel.setBones(boneList)
	results.setSkeleton(skel)
	results.setMeshes(list(meshes.values()))
	#results.setMaterials(resultMaterials)
	if printProgress:
		print("Finished parsing .brres file.")
	return results

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
	results = []
	for subfile in globalDict.items():
		subfileName,subfileOffset = subfile
		f.seek(subfileOffset)
		submagic = f.read(4)
		# there's a common format to the subfile headers, but it's more convenient to pretend otherwise
		# was going to set this up with some cleverness about a function map, but decided it was overcomplicating things
		if submagic == b"MDL0":
			results.append(parse_mdl0(f,context,subfileOffset))
		else:
			print_warning(str(submagic)+" files not yet supported, skipping")
	
	return results[0]

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