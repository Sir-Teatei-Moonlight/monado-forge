import bpy
import io
#import math
import mathutils
import os
import traceback
import zlib
from bpy.props import (
						BoolProperty,
						EnumProperty,
						FloatProperty,
						PointerProperty,
						StringProperty,
						)
from bpy.types import (
						Operator,
						Panel,
						PropertyGroup,
						)

from . utils import *

def import_wimdo(f, context):
	printProgress = context.scene.xb_tools.printProgress
	# little endian assumed
	magic = f.read(4)
	if magic != b"DMXM":
		raise ValueError("Not a valid .wimdo file (unexpected header)")
	version = readAndParseInt(f,4)
	modelsOffset = readAndParseInt(f,4)
	materialsOffset = readAndParseInt(f,4)
	unknown1 = readAndParseInt(f,4)
	vertexBufferOffset = readAndParseInt(f,4)
	shadersOffset = readAndParseInt(f,4)
	cachedTexturesTableOffset = readAndParseInt(f,4)
	unknown2 = readAndParseInt(f,4)
	uncachedTexturesTableOffset = readAndParseInt(f,4)
	
	# assumption: there can be only one skeleton per .wimdo
	forgeBones = []
	meshHeaders = []
	shapeHeaders = []
	shapeNames = []
	
	if modelsOffset > 0:
		f.seek(modelsOffset)
		meshesUnknown1 = readAndParseInt(f,4)
		boundingBoxStart = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
		boundingBoxEnd = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
		meshDataOffset = readAndParseInt(f,4)
		meshCount = readAndParseInt(f,4)
		meshesUnknown2 = readAndParseInt(f,4)
		bonesOffset = readAndParseInt(f,4)
		f.seek(f.tell()+21*4) # skip these unknowns
		shapeItemsOffset = readAndParseInt(f,4)
		shapeNamesOffset = readAndParseInt(f,4)
		f.seek(modelsOffset+21*4) # skip s'more
		lodsOffset = readAndParseInt(f,4)
		
		if meshCount > 0:
			f.seek(modelsOffset+meshDataOffset)
			for i in range(meshCount):
				meshTableOffset = readAndParseInt(f,4)
				meshTableCount = readAndParseInt(f,4)
				meshUnknown1 = readAndParseInt(f,4)
				meshBoundingBoxStart = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
				meshBoundingBoxEnd = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
				meshBoundingRadius = readAndParseFloat(f)
				f.seek(modelsOffset+meshTableOffset)
				for j in range(meshTableCount):
					meshID = readAndParseInt(f,4)
					meshFlags = readAndParseInt(f,4)
					meshVertTableIndex = readAndParseInt(f,2)
					meshFaceTableIndex = readAndParseInt(f,2)
					f.seek(f.tell()+2) # skip unknown
					meshMaterialIndex = readAndParseInt(f,2)
					f.seek(f.tell()+14) # skip unknown
					meshLODValue = readAndParseInt(f,2)
					f.seek(f.tell()+16) # skip unknown
					meshHeaders.append(MonadoForgeMeshHeader(meshID,meshFlags,meshVertTableIndex,meshFaceTableIndex,meshMaterialIndex,meshLODValue))
			if printProgress:
				print("Found "+str(len(meshHeaders))+" mesh headers.")
		
		if bonesOffset > 0:
			f.seek(modelsOffset+bonesOffset)
			boneCount = readAndParseInt(f,4)
			boneCount2 = readAndParseInt(f,4)
			boneHeaderOffset = readAndParseInt(f,4)
			boneMatrixesOffset = readAndParseInt(f,4)
			bonesUnknown1 = readAndParseInt(f,4)
			bonesUnknown2 = readAndParseInt(f,4) # claimed by XBC2MD to be "positions offset", but that's part of the matrixes
			bonePairsOffset = readAndParseInt(f,4)
			
			for b in range(boneCount):
				f.seek(modelsOffset+bonesOffset+boneHeaderOffset+b*6*4)
				nameOffset = readAndParseInt(f,4)
				boneUnknown1 = readAndParseInt(f,4)
				boneType = readAndParseInt(f,4)
				boneIndex = readAndParseInt(f,4)
				f.seek(modelsOffset+bonesOffset+nameOffset)
				boneName = readStr(f)
				f.seek(modelsOffset+bonesOffset+boneMatrixesOffset+b*16*4)
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
				fb.setPosition(bonePosition[:]) # the [:] is because we're turning a Vector into a list
				fb.setRotation(rotMatrix.to_quaternion())
				forgeBones.append(fb)
			if printProgress:
				print("Found "+str(len(forgeBones))+" bones.")
		
		if shapeItemsOffset > 0:
			f.seek(modelsOffset+shapeItemsOffset)
			shapeHeaderOffset = readAndParseInt(f,4)
			shapeHeaderCount = readAndParseInt(f,4)
			for i in range(shapeHeaderCount):
				f.seek(modelsOffset+shapeItemsOffset+shapeHeaderOffset+i*7*4)
				shapeNameOffset1 = readAndParseInt(f,4)
				shapeNameOffset2 = readAndParseInt(f,4)
				# it's unclear what the difference in these is supposed to be (the resulting strings seem to always be the same)
				# there's a bunch of other stuff here but it doesn't seem like we need it?
				f.seek(modelsOffset+shapeItemsOffset+shapeNameOffset1)
				shapeName1 = readStr(f)
				f.seek(modelsOffset+shapeItemsOffset+shapeNameOffset2)
				shapeName2 = readStr(f)
				shapeHeaders.append([shapeName1])
			if printProgress:
				print("Found "+str(len(shapeHeaders))+" shape headers.")
		# apparently you can have shapes with controllers without names? odd
		if shapeNamesOffset > 0:
			f.seek(modelsOffset+shapeNamesOffset)
			shapeNameTableOffset = readAndParseInt(f,4)
			shapeNameTableCount = readAndParseInt(f,4)
			for i in range(shapeNameTableCount):
				f.seek(modelsOffset+shapeNamesOffset+shapeNameTableOffset+i*4*4)
				shapeNameOffset = readAndParseInt(f,4)
				f.seek(modelsOffset+shapeNamesOffset+shapeNameOffset)
				shapeNames.append(readStr(f))
	
	if materialsOffset > 0:
		f.seek(materialsOffset)
	if vertexBufferOffset > 0:
		f.seek(vertexBufferOffset)
	if shadersOffset > 0:
		f.seek(shadersOffset)
	if cachedTexturesTableOffset > 0:
		f.seek(cachedTexturesTableOffset)
	if uncachedTexturesTableOffset > 0: # don't need this for the texture files themselves - it's for metadata (alpha, repeat, etc)
		f.seek(uncachedTexturesTableOffset)
	
	skeleton = MonadoForgeSkeleton()
	skeleton.setBones(forgeBones)
	results = MonadoForgeWimdoPackage(skeleton,meshHeaders,shapeHeaders)
	if printProgress:
		print("Finished parsing .wimdo file.")
	return results

def extract_wismt_subfile(f, headerOffset):
	f.seek(headerOffset)
	compressedSize = readAndParseInt(f,4)
	uncompressedSize = readAndParseInt(f,4)
	dataOffset = readAndParseInt(f,4)
	f.seek(dataOffset)
	submagic = f.read(4)
	if submagic != b"xbc1":
		raise ValueError("subfile at "+str(headerOffset)+" has an invalid header (not \"xbc1\")")
	subfileVersion = readAndParseInt(f,4)
	subfileSize = readAndParseInt(f,4)
	subfileCompressedSize = readAndParseInt(f,4)
	subfileUnknown1 = readAndParseInt(f,4)
	subfileName = readFixedLenStr(f,28)
	content = zlib.decompress(f.read(subfileCompressedSize))
	if len(content) != subfileSize:
		raise ValueError("subfile "+subfileName+" did not decompress to its claimed size: "+str(len(content))+" != "+str(subfileSize))
	return subfileName,content

def import_wismt(f, wimdoResults, context):
	printProgress = context.scene.xb_tools.printProgress
	# little endian assumed
	# renamed some stuff from older programs to make more sense:
	# data items -> content pointers
	# TOC -> subfile headers
	magic = f.read(4)
	if magic != b"DRSM":
		raise ValueError("Not a valid .wismt file (unexpected header)")
	version = readAndParseInt(f,4)
	headerSize = readAndParseInt(f,4)
	mainOffset = readAndParseInt(f,4)
	tag = readAndParseInt(f,4)
	revision = readAndParseInt(f,4)
	contentPointersCount = readAndParseInt(f,4)
	contentPointersOffset = readAndParseInt(f,4)
	subfileCount = readAndParseInt(f,4)
	subfileHeadersOffset = readAndParseInt(f,4)
	f.seek(f.tell()+7*4)
	textureIDsCount = readAndParseInt(f,4)
	textureIDsOffset = readAndParseInt(f,4)
	textureCountOffset = readAndParseInt(f,4)
	
	# here is the deal:
	# content pointers can be models, shaders, cached textures, or uncached textures
	# models, shaders, and cached textures (low-res) point to subfile[0]
	# uncached textures (mid-res) point to subfile[1] and have a subfile index for their high-res version
	# both use their internalOffset within their subfile
	# the remaining subfiles (no matching content pointers) are high-res textures
	
	contentPointers = []
	hasContentType = [False,False,False,False] # model, shader, cached texture, uncached texture
	if contentPointersCount > 0:
		for i in range(contentPointersCount):
			f.seek(mainOffset+contentPointersOffset+i*5*4)
			internalOffset = readAndParseInt(f,4)
			contentSize = readAndParseInt(f,4)
			highResSubfileIndex = readAndParseInt(f,2) - 1 # the -1 is needed to align properly
			contentType = readAndParseInt(f,2)
			hasContentType[contentType] = True
			contentPointers.append([internalOffset,contentSize,highResSubfileIndex,contentType])
	textureIDList = []
	if textureIDsOffset > 0:
		f.seek(mainOffset+textureIDsOffset)
		for i in range(textureIDsCount):
			textureIDList.append(readAndParseInt(f,2))
	textureHeaders = []
	if textureCountOffset > 0:
		f.seek(mainOffset+textureCountOffset)
		textureCount = readAndParseInt(f,4)
		textureChunkSize = readAndParseInt(f,4)
		textureUnknown = readAndParseInt(f,4)
		textureStringsOffset = readAndParseInt(f,4)
		for i in range(textureCount):
			textureUnknown1 = readAndParseInt(f,4)
			textureFilesize = readAndParseInt(f,4)
			textureOffset = readAndParseInt(f,4)
			textureNameOffset = readAndParseInt(f,4)
			tempOffset = f.tell()
			f.seek(mainOffset+textureCountOffset+textureNameOffset)
			textureName = readStr(f)
			f.seek(tempOffset)
			textureHeaders.append([textureFilesize,textureOffset,textureNameOffset,textureName])
		# not really sure why this is here, but it's in XBC2MD, so there must be a reason for it
		# special case: if these offsets are the same, the IDs are in a different spot than usual (i.e. here right after the headers)
		if textureIDsOffset == textureCountOffset:
			textureIDList = []
			for i in range(textureCount):
				textureIDList.append(readAndParseInt(f,2))
	
	meshes = []
	vertexWeights = {}
	nextSubfileIndex = 0
	hasRootSubfile = hasContentType[0] or hasContentType[1] or hasContentType[2]
	hasMedResSubfile = hasContentType[3]
	if hasRootSubfile:
		subfileHeaderOffset = mainOffset+subfileHeadersOffset+nextSubfileIndex*3*4
		subfileName,subfileData = extract_wismt_subfile(f,subfileHeaderOffset)
		for cp in contentPointers:
			internalOffset,contentSize,highResSubfileIndex,contentType = cp
			if contentType == 0: # model
				data = subfileData[internalOffset:internalOffset+contentSize]
				if printProgress:
					print("Opening model subfile.")
				sf = io.BytesIO(data)
				try: # no except, just finally (to close sf)
					vertexTableOffset = readAndParseInt(sf,4)
					vertexTableCount = readAndParseInt(sf,4)
					faceTableOffset = readAndParseInt(sf,4)
					faceTableCount = readAndParseInt(sf,4)
					sf.seek(sf.tell()+6*4)
					shapeDataOffset = readAndParseInt(sf,4)
					dataSize = readAndParseInt(sf,4)
					dataOffset = readAndParseInt(sf,4)
					weightDataSize = readAndParseInt(sf,4)
					weightDataOffset = readAndParseInt(sf,4)
					# another 0x14 mystery reads
					vertexTables = []
					faceTables = []
					weightTables = []
					shapeHeaders = []
					shapeTargets = []
					shapes = []
					if vertexTableOffset > 0: # not sure how we can have a mesh without vertexes, but okay
						for i in range(vertexTableCount):
							sf.seek(vertexTableOffset+i*8*4)
							vtDataOffset = readAndParseInt(sf,4)
							vtDataCount = readAndParseInt(sf,4)
							vtBlockSize = readAndParseInt(sf,4)
							vtDescOffset = readAndParseInt(sf,4)
							vtDescCount = readAndParseInt(sf,4)
							# 3 unknowns
							sf.seek(vtDescOffset)
							vertexDescriptors = []
							for j in range(vtDescCount):
								vdType = readAndParseInt(sf,2)
								vdSize = readAndParseInt(sf,2)
								vertexDescriptors.append([vdType,vdSize])
							vertexTables.append([vtDataOffset,vtDataCount,vtBlockSize,vtDescOffset,vtDescCount,vertexDescriptors])
						if printProgress:
							print("Found "+str(len(vertexTables))+" vertex tables.")
					if faceTableOffset > 0:
						for i in range(faceTableCount):
							sf.seek(faceTableOffset+i*5*4)
							ftDataOffset = readAndParseInt(sf,4)
							ftVertCount = readAndParseInt(sf,4)
							# 3 unknowns
							sf.seek(dataOffset+ftDataOffset)
							ftVertexes = []
							for j in range(ftVertCount):
								ftVertexes.append(readAndParseInt(sf,2))
							faceTables.append([ftDataOffset,ftVertCount,ftVertexes])
						if printProgress:
							print("Found "+str(len(faceTables))+" face tables.")
					if weightDataOffset > 0:
						sf.seek(weightDataOffset)
						weightTableCount = readAndParseInt(sf,4)
						weightTableOffset = readAndParseInt(sf,4)
						weightVertTableIndex = readAndParseInt(sf,2)
						# then a couple unknowns
						sf.seek(weightTableOffset)
						for i in range(weightTableCount):
							# buncha unknowns in here, might not use it necessarily
							sf.seek(sf.tell()+4)
							wtDataOffset = readAndParseInt(sf,4)
							wtDataCount = readAndParseInt(sf,4)
							sf.seek(sf.tell()+17)
							wtLOD = readAndParseInt(sf,1)
							sf.seek(sf.tell()+10)
							weightTables.append([wtDataOffset,wtDataCount,wtLOD])
						if printProgress:
							print("Found "+str(len(weightTables))+" weight tables.")
					if shapeDataOffset > 0:
						sf.seek(shapeDataOffset)
						shapeHeaderCount = readAndParseInt(sf,4)
						shapeHeaderOffset = readAndParseInt(sf,4)
						shapeTargetCount = readAndParseInt(sf,4)
						shapeTargetOffset = readAndParseInt(sf,4)
						sf.seek(shapeHeaderOffset)
						for i in range(shapeHeaderCount):
							shapeDataChunkID = readAndParseInt(sf,4)
							shapeTargetIndex = readAndParseInt(sf,4)
							shapeTargetCounts = readAndParseInt(sf,4)
							shapeTargetIDOffset = readAndParseInt(sf,4)
							dummy = readAndParseInt(sf,4)
							shapeHeaders.append([shapeDataChunkID,shapeTargetIndex,shapeTargetCounts,shapeTargetIDOffset])
						sf.seek(shapeTargetOffset)
						for i in range(shapeTargetCount):
							targetDataChunkOffset = readAndParseInt(sf,4)
							targetVertexCount = readAndParseInt(sf,4)
							targetBlockSize = readAndParseInt(sf,4)
							targetUnknown = readAndParseInt(sf,2)
							targetType = readAndParseInt(sf,2)
							shapeTargets.append([targetDataChunkOffset,targetVertexCount,targetBlockSize,targetUnknown,targetType])
						if printProgress:
							print("Found "+str(len(shapeTargets))+" shapekeys.")
					
					# tables ready, now read the actual data
					unknownVDTypes = {}
					vertexData = {}
					faceData = {}
					vertexWeightData = {} # assumption: a single vertex cannot both contain actual data and be one of the "weight container only" vertices
					for i in range(len(vertexTables)):
						vertexData[i] = []
						vertexWeightData[i] = []
						vtDataOffset,vtDataCount,vtBlockSize,vtDescOffset,vtDescCount,vertexDescriptors = vertexTables[i]
						newMesh = MonadoForgeMesh()
						sf.seek(dataOffset+vtDataOffset)
						for j in range(vtDataCount):
							newVertex = MonadoForgeVertex()
							weightVertex = [[],[]]
							for vd in vertexDescriptors:
								vdType,vdSize = vd
								if vdType == 0: # position
									newVertex.setPosition([readAndParseFloat(sf),readAndParseFloat(sf),readAndParseFloat(sf)])
								elif vdType == 3: # weights index
									newVertex.setWeightSetIndex(readAndParseInt(sf,4))
								elif vdType == 5: # UV 1 (inverted Y reminder) (yes this is copy/pasted for other layers but this is kind of easier actually)
									newVertex.setUV(0,[readAndParseFloat(sf),1.0-readAndParseFloat(sf)])
								elif vdType == 6: # UV 2
									newVertex.setUV(1,[readAndParseFloat(sf),1.0-readAndParseFloat(sf)])
								elif vdType == 7: # UV 3
									newVertex.setUV(2,[readAndParseFloat(sf),1.0-readAndParseFloat(sf)])
								elif vdType == 17: # colour
									a,r,g,b = readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1)
									newVertex.setColour([r,g,b,a])
								elif vdType == 28: # normals
									newNormal = [readAndParseInt(sf,1,signed=True)/128.0,readAndParseInt(sf,1,signed=True)/128.0,readAndParseInt(sf,1,signed=True)/128.0]
									readAndParseInt(sf,1,signed=True) # dummy
									# doesn't necessarily read as normalized
									newVertex.setNormal(mathutils.Vector(newNormal).normalized()[:])
								elif vdType == 41: # weight values (weightTable verts only)
									weightVertex[1] = [readAndParseInt(sf,2)/65535.0,readAndParseInt(sf,2)/65535.0,readAndParseInt(sf,2)/65535.0,readAndParseInt(sf,2)/65535.0]
								elif vdType == 42: # weight IDs (weightTable verts only)
									weightVertex[0] = [readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1)]
								else:
									unknownVDTypes[vdType] = vdSize
									sf.seek(sf.tell()+vdSize)
							newMesh.addVertex(newVertex)
							vertexData[i].append(newVertex)
							vertexWeightData[i].append(weightVertex)
					if printProgress and vertexData != {}:
						print("Finished reading vertex data.")
					if unknownVDTypes:
						print("unknownVDTypes: "+str(unknownVDTypes))
					for i in range(len(faceTables)):
						faceData[i] = []
						ftDataOffset,ftVertCount,ftVertexes = faceTables[i]
						for j in range(0,len(ftVertexes),3):
							newFace = MonadoForgeFace()
							newFace.setVertexIndexes([ftVertexes[j],ftVertexes[j+1],ftVertexes[j+2]])
							faceData[i].append(newFace)
					if printProgress and faceData != {}:
						print("Finished reading face data.")
					for i in range(len(shapeHeaders)):
						shapeDataChunkID,shapeTargetIndex,shapeTargetCounts,shapeTargetIDOffset = shapeHeaders[i]
						targetDataChunkOffset,targetVertexCount,targetBlockSize,targetUnknown,targetType = shapeTargets[shapeTargetIndex]
						sf.seek(shapeTargetIDOffset)
						targetIDs = []
						for j in range(shapeTargetCounts):
							targetIDs.append(readAndParseInt(sf,2))
						sf.seek(dataOffset+targetDataChunkOffset)
						# first, get the base shape
						# it seems that "has shapes" is the difference for whether normals are signed or not
						for j in range(targetVertexCount):
							vertexBeingModified = vertexData[shapeDataChunkID][j]
							vertexBeingModified.setPosition([readAndParseFloat(sf),readAndParseFloat(sf),readAndParseFloat(sf)])
							newNormal = [(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1]
							# doesn't necessarily read as normalized
							vertexBeingModified.setNormal(mathutils.Vector(newNormal).normalized()[:])
							sf.seek(sf.tell()+targetBlockSize-15) # the magic -15 is the length of the position+normal (4*3 + 3)
						shapeNameList = ["basis"] + [h[0] for h in wimdoResults.getShapeHeaders()] # "basis" needs to be added because the first target is also the base shape for some reason
						for j in range(shapeTargetCounts+1):
							if j == 0: continue # as above, the first is the basis so we don't need it
							# it's okay to overwrite these variables, we don't need the above ones anymore
							targetDataChunkOffset,targetVertexCount,targetBlockSize,targetUnknown,targetType = shapeTargets[shapeTargetIndex+j+1]
							sf.seek(dataOffset+targetDataChunkOffset)
							newShape = MonadoForgeMeshShape()
							for k in range(targetVertexCount):
								newVertex = MonadoForgeVertex()
								newVertex.setPosition([readAndParseFloat(sf),readAndParseFloat(sf),readAndParseFloat(sf)])
								readAndParseInt(sf,4) # dummy
								newNormal = [(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1]
								readAndParseInt(sf,1) # more dummies
								readAndParseInt(sf,4)
								readAndParseInt(sf,4)
								index = readAndParseInt(sf,4)
								# doesn't necessarily read as normalized
								newVertex.setNormal(mathutils.Vector(newNormal).normalized()[:])
								newShape.addVertex(index,newVertex)
							newShape.setVertexTableIndex(shapeDataChunkID)
							newShape.setName(shapeNameList[j]) # probably wrong but need to find a counterexample
							shapes.append(newShape)
					if printProgress and shapes != []:
						print("Finished reading shape data.")
					shapesByVertexTableIndex = {}
					for s in shapes:
						thisShapesIndex = s.getVertexTableIndex()
						if thisShapesIndex in shapesByVertexTableIndex.keys():
							shapesByVertexTableIndex[thisShapesIndex].append(s)
						else:
							shapesByVertexTableIndex[thisShapesIndex] = [s]
					
					unusedVertexTables = [k for k in vertexData.keys()]
					unusedFaceTables = [k for k in faceData.keys()]
					bestLOD = wimdoResults.getBestLOD()
					# do the special weight table vertices first
					if weightDataOffset > 0: # has weights
						unusedVertexTables.remove(weightVertTableIndex)
						for v in range(len(vertexWeightData[weightVertTableIndex])):
							vertexWeights[v] = [vertexWeightData[weightVertTableIndex][v][0],vertexWeightData[weightVertTableIndex][v][1]]
					# we can "bake" the vertices with their weights now (but they keep the index in case it's more useful later)
					for i,vertices in vertexData.items():
						for v in vertices:
							weightIndex = v.getWeightSetIndex()
							if weightIndex == -1: continue
							for j in range(len(vertexWeights[weightIndex][0])):
								if vertexWeights[weightIndex][1][j] > 0:
									v.setWeight(vertexWeights[weightIndex][0][j],vertexWeights[weightIndex][1][j])
					# now for the meshes themselves
					for md in wimdoResults.getMeshHeaders():
						vtIndex = md.getMeshVertTableIndex()
						ftIndex = md.getMeshFaceTableIndex()
						if vtIndex in unusedVertexTables:
							unusedVertexTables.remove(vtIndex)
						if ftIndex in unusedFaceTables:
							unusedFaceTables.remove(ftIndex)
						# this order of operations means that tables are still "used" even if they're of dropped LODs
						if not context.scene.xb_tools_model.alsoImportLODs:
							if md.getMeshLODValue() > bestLOD:
								continue
						newMesh = MonadoForgeMesh()
						newMesh.setVertices(vertexData[vtIndex])
						newMesh.setFaces(faceData[ftIndex])
						newMesh.setWeightSets(vertexWeights)
						if vtIndex in shapesByVertexTableIndex.keys():
							newMesh.setShapes(shapesByVertexTableIndex[vtIndex])
						meshes.append(newMesh)
					if unusedVertexTables:
						print("Unused vertex tables: "+str(unusedVertexTables))
					if unusedFaceTables:
						print("Unused face tables: "+str(unusedFaceTables))
					if printProgress:
						print("Finished processing mesh data.")
				finally:
					sf.close()
			if contentType == 1: # shader
				data = subfileData[internalOffset:internalOffset+contentSize]
				if printProgress:
					print("Found shader chunk of size "+str(contentSize)+" (not supported, skipping)")
				pass
			if contentType == 2: # cached texture
				data = subfileData[internalOffset:internalOffset+contentSize]
				sf = io.BytesIO(data)
				try: # no except, just finally (to close sf)
					for i in range(len(textureHeaders)):
						textureFilesize,textureOffset,textureNameOffset,textureName = textureHeaders[i]
						# for some reason, this stuff is in reverse order: first data, then properties (in reverse order), and magic at end
						sf.seek(textureOffset+textureFilesize-0x4)
						submagic = sf.read(4)
						if submagic != b"LBIM":
							print("Bad cached texture (invalid subfilemagic); skipping "+str(textureName))
						else:
							sf.seek(textureOffset+textureFilesize-0x28)
							subfileUnknown5 = readAndParseInt(sf,4)
							subfileUnknown4 = readAndParseInt(sf,4)
							imgWidth = readAndParseInt(sf,4)
							imgHeight = readAndParseInt(sf,4)
							subfileUnknown3 = readAndParseInt(sf,4)
							subfileUnknown2 = readAndParseInt(sf,4)
							imgType = readAndParseInt(sf,4)
							subfileUnknown1 = readAndParseInt(sf,4)
							imgVersion = readAndParseInt(sf,4)
							if printProgress:
								print(f"Found cached texture: name {textureName}, size {imgWidth}x{imgHeight}, format {imgType}")
							sf.seek(textureOffset)
							parse_texture(textureName,imgVersion,imgType,imgWidth,imgHeight,sf.read(textureFilesize),context.scene.xb_tools_model.blueBC5)
				finally:
					sf.close()
		del subfileData # just to ensure it's cleaned up as soon as possible
		nextSubfileIndex += 1
	if hasMedResSubfile and context.scene.xb_tools_model.alsoImportMipmaps:
		subfileHeaderOffset = mainOffset+subfileHeadersOffset+nextSubfileIndex*3*4
		subfileName,subfileData = extract_wismt_subfile(f,subfileHeaderOffset)
		for cpi,cp in enumerate(contentPointers):
			internalOffset,contentSize,highResSubfileIndex,contentType = cp
			if contentType == 3: # med-res texture
				data = subfileData[internalOffset:internalOffset+contentSize]
				sf = io.BytesIO(data)
				try: # no except, just finally (to close sf)
					textureName = textureHeaders[textureIDList[cpi-3]][3]
					# for some reason, this stuff is in reverse order: first data, then properties (in reverse order), and magic at end
					sf.seek(contentSize-0x4)
					submagic = sf.read(4)
					if submagic != b"LBIM":
						print("Bad cached texture (invalid subfilemagic); skipping "+str(textureName))
					else:
						sf.seek(contentSize-0x28)
						subfileUnknown5 = readAndParseInt(sf,4)
						subfileUnknown4 = readAndParseInt(sf,4)
						imgWidth = readAndParseInt(sf,4)
						imgHeight = readAndParseInt(sf,4)
						subfileUnknown3 = readAndParseInt(sf,4)
						subfileUnknown2 = readAndParseInt(sf,4)
						imgType = readAndParseInt(sf,4)
						subfileUnknown1 = readAndParseInt(sf,4)
						imgVersion = readAndParseInt(sf,4)
						if printProgress:
							print(f"Found med-res texture: name {textureName}, size {imgWidth}x{imgHeight}, format {imgType}")
						sf.seek(0)
						parse_texture(textureName+"_medRes",imgVersion,imgType,imgWidth,imgHeight,sf.read(),context.scene.xb_tools_model.blueBC5)
				finally:
					sf.close()
		del subfileData
		nextSubfileIndex += 1
	# at this point, any remaining subfiles ought to be full-size textures
	while nextSubfileIndex < subfileCount:
		textureName = textureHeaders[textureIDList[nextSubfileIndex-2]][3]
		#subfileHeaderOffset = mainOffset+subfileHeadersOffset+nextSubfileIndex*3*4
		#subfileName,subfileData = extract_wismt_subfile(f,subfileHeaderOffset)
		if printProgress:
			print(f"Found full-size texture: name {textureName} (not doing anything with it yet)")
		nextSubfileIndex += 1
	
	for m in meshes:
		m.indexVertices()
	results = MonadoForgeImportedPackage()
	results.addSkeleton(wimdoResults.getSkeleton())
	results.setMeshes(meshes)
	if printProgress:
		print("Finished parsing .wismt file.")
	return results

def import_wimdo_only(self, context):
	absoluteDefsPath = bpy.path.abspath(context.scene.xb_tools_model.defsPath)
	if context.scene.xb_tools.printProgress:
		print("Importing model from: "+absoluteDefsPath)
	
	if os.path.splitext(absoluteDefsPath)[1] != ".wimdo":
		self.report({"ERROR"}, "File was not a .wimdo file")
		return {"CANCELLED"}
	
	with open(absoluteDefsPath, "rb") as f:
		forgeResults = import_wimdo(f, context)
	return realise_results(forgeResults, os.path.splitext(os.path.basename(absoluteDefsPath))[0], self, context)

def import_wimdo_and_wismt(self, context):
	absoluteDefsPath = bpy.path.abspath(context.scene.xb_tools_model.defsPath)
	absoluteDataPath = bpy.path.abspath(context.scene.xb_tools_model.dataPath)
	if context.scene.xb_tools.printProgress:
		print("Importing model from: "+absoluteDefsPath+" & "+absoluteDataPath)
	
	if os.path.splitext(absoluteDefsPath)[1] != ".wimdo":
		self.report({"ERROR"}, "First file was not a .wimdo file")
		return {"CANCELLED"}
	if os.path.splitext(absoluteDataPath)[1] != ".wismt":
		self.report({"ERROR"}, "Second file was not a .wismt file")
		return {"CANCELLED"}
	
	with open(absoluteDefsPath, "rb") as f:
		wimdoResults = import_wimdo(f, context)
	with open(absoluteDataPath, "rb") as f:
		wismtResults = import_wismt(f, wimdoResults, context)
	return realise_results(wismtResults, os.path.splitext(os.path.basename(absoluteDataPath))[0], self, context)

def realise_results(forgeResults, mainName, self, context):
	printProgress = context.scene.xb_tools.printProgress
	if not forgeResults:
		self.report({"ERROR"}, "Compiled results were empty. There might be more information in the console.")
		return {"CANCELLED"}
	if printProgress:
		print("Converting processed data into Blender objects.")
	skeletons = forgeResults.getSkeletons()
	armatures = []
	for skeleton in skeletons:
		boneList = skeleton.getBones()
		armatureName = mainName
		if context.scene.xb_tools_model.useSkeletonSettings:
			boneSize = context.scene.xb_tools_skeleton.boneSize
			positionEpsilon = context.scene.xb_tools_skeleton.positionEpsilon
			angleEpsilon = context.scene.xb_tools_skeleton.angleEpsilon
		else:
			boneSize = 0.1
			positionEpsilon = 0.0001
			angleEpsilon = math.radians(0.1)
		armatures.append(create_armature_from_bones(boneList,armatureName,boneSize,positionEpsilon,angleEpsilon))
	# attach to the first armature created (this logic might change later)
	targetArmature = armatures[0]
	if printProgress:
		print("Finished creating "+str(len(armatures))+" armatures.")
	meshes = forgeResults.getMeshes()
	for m,mesh in enumerate(meshes):
		bpy.ops.object.add(type="MESH", enter_editmode=False, align="WORLD", location=context.scene.cursor.location, rotation=(0,0,0), scale=(1,1,1))
		newMeshObject = bpy.context.view_layer.objects.active
		newMeshObject.name = f"{mainName}_mesh{m:03d}"
		meshData = newMeshObject.data
		meshData.name = "Mesh"
		vertCount = len(mesh.getVertices())
		meshData.from_pydata(mesh.getVertexPositionsList(),[],mesh.getFaceVertexIndexesList())
		for f in meshData.polygons:
			f.use_smooth = True
		meshData.use_auto_smooth = True
		if mesh.hasUVs():
			for layer in mesh.getUVLayerList():
				meshUVs = mesh.getVertexUVsLayer(layer)
				newUVsLayer = meshData.uv_layers.new(name="UV"+str(layer+1))
				for l in meshData.loops:
					newUVsLayer.data[l.index].uv = meshUVs[l.vertex_index]
		if mesh.hasNormals():
			normalsList = mesh.getVertexNormalsList()
			meshData.normals_split_custom_set_from_vertices(normalsList)
		if mesh.hasColours():
			coloursList = mesh.getVertexColoursList()
			vertCols = meshData.color_attributes.new("VertexColours","BYTE_COLOR","POINT")
			for i in range(len(coloursList)):
				vertCols.data[i].color = coloursList[i]
		if mesh.hasWeightIndexes(): # try the indexes method first (faster)
			weightIndexes = set(mesh.getVertexWeightIndexesList())
			vertexesInEachGroup = {}
			for i in range(len(targetArmature.data.bones)):
				newMeshObject.vertex_groups.new(name=targetArmature.data.bones[i].name)
				vertexesInEachGroup[i] = mesh.getVertexesInWeightGroup(i)
			weightSets = mesh.getWeightSets()
			for i,weightIndex in enumerate(weightIndexes):
				weightSetData = weightSets[weightIndex]
				for j in range(len(weightSetData[0])):
					groupIndex = weightSetData[0][j]
					groupValue = weightSetData[1][j]
					if groupValue == 0: continue
					vertexGroup = newMeshObject.vertex_groups[groupIndex]
					vertexesToAdd = vertexesInEachGroup[groupIndex]
					vertexIDsToAdd = [v.getID() for v in vertexesToAdd]
					newMeshObject.vertex_groups[groupIndex].add(vertexIDsToAdd,groupValue,"ADD")
		elif mesh.hasWeights(): # no indexes, but do have directly-applied weights
			pass # not needed at the present time
		if mesh.hasShapes():
			shapes = mesh.getShapes()
			if not meshData.shape_keys:
				newMeshObject.shape_key_add(name="basis",from_mix=False)
			meshData.shape_keys.use_relative = True
			for s in shapes:
				newShape = newMeshObject.shape_key_add(name=s.getName(),from_mix=False)
				for vertexIndex,vertex in s.getVertices().items():
					newShape.data[vertexIndex].co += mathutils.Vector(vertex.getPosition())
		if printProgress:
			print("Created mesh "+str(m)+".")
		
		# import complete, cleanup time
		#meshData.validate(verbose=True)
		meshData.validate()
		meshData.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix().to_4x4(),shape_keys=True) # transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
		cleanup_mesh(context,newMeshObject,context.scene.xb_tools_model.cleanupLooseVertices,context.scene.xb_tools_model.cleanupEmptyGroups,context.scene.xb_tools_model.cleanupEmptyShapes)
		# attach mesh to armature
		armatureMod = newMeshObject.modifiers.new("Armature","ARMATURE")
		armatureMod.object = targetArmature
		newMeshObject.parent = targetArmature
	if printProgress:
		print("Finished creating "+str(len(meshes))+" meshes.")
	return {"FINISHED"}

class XBModelImportOperator(Operator):
	bl_idname = "object.xb_tools_model_operator"
	bl_label = "Xenoblade Model Import Operator"
	bl_description = "Imports a model from a Xenoblade file"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		# can't import a .wismt without a .wimdo (requires vertex table + face table alignment)
		return context.scene.xb_tools_model.singlePath or context.scene.xb_tools_model.defsPath # or context.scene.xb_tools_model.dataPath
	
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
			self.report({"ERROR"}, "Unexpected error; code shouldn't be able to reach here")
			return {"CANCELLED"}
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}

class XBModelCleanupOperator(Operator):
	bl_idname = "object.xb_tools_model_cleanup_operator"
	bl_label = "Xenoblade Model Cleanup Operator"
	bl_description = "Does selected clean up operations to all selected meshes"
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
				cleanup_mesh(context,obj,context.scene.xb_tools_model.cleanupLooseVertices,context.scene.xb_tools_model.cleanupEmptyGroups,context.scene.xb_tools_model.cleanupEmptyShapes)
			return {"FINISHED"}
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
	blueBC5 : BoolProperty(
		name="Normalize BC5s",
		description="Assume that BC5-format images are normal maps, and calculate the blue channel accordingly",
		default=True,
	)
	alsoImportMipmaps : BoolProperty(
		name="Also Import Mipmaps",
		description="Include non-full-size uncached textures (\"medium resolution\") in the import",
		default=True,
	)

class OBJECT_PT_XBModelToolsPanel(Panel):
	bl_idname = "OBJECT_PT_XBModelToolsPanel"
	bl_label = "Model"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_XBToolsPanel"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		importPanel = col.column(align=True)
		importPanel.label(text="Import")
		if scn.xb_tools.game == "XC1":
			importPanel.prop(scn.xb_tools_model, "singlePath", text=".brres")
		else:
			defsRow = importPanel.row()
			defsRow.prop(scn.xb_tools_model, "defsPath", text=".wimdo")
			dataRow = importPanel.row()
			dataRow.prop(scn.xb_tools_model, "dataPath", text=".wismt")
		importPanel.prop(scn.xb_tools_model, "useSkeletonSettings")
		importPanel.prop(scn.xb_tools_model, "alsoImportLODs")
		importPanel.prop(scn.xb_tools_model, "doCleanupOnImport")
		importPanel.operator(XBModelImportOperator.bl_idname, text="Import Model", icon="IMPORT")
		importPanel.separator()
		importPanel.operator(XBModelCleanupOperator.bl_idname, text="Clean Up Selected Meshes", icon="BRUSH_DATA")

class OBJECT_PT_XBModelToolsCleanupPanel(Panel):
	bl_idname = "OBJECT_PT_XBModelToolsCleanupPanel"
	bl_label = "Model Cleanup"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_XBModelToolsPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.xb_tools_model, "cleanupLooseVertices")
		col.prop(scn.xb_tools_model, "cleanupEmptyGroups")
		col.prop(scn.xb_tools_model, "cleanupEmptyShapes")

class OBJECT_PT_XBModelToolsTexturePanel(Panel):
	bl_idname = "OBJECT_PT_XBModelToolsTexturePanel"
	bl_label = "Textures"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_XBModelToolsPanel"
	
	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.xb_tools_model, "blueBC5")
		col.prop(scn.xb_tools_model, "alsoImportMipmaps")

classes = (
			XBModelImportOperator,
			XBModelCleanupOperator,
			XBModelToolsProperties,
			OBJECT_PT_XBModelToolsPanel,
			OBJECT_PT_XBModelToolsCleanupPanel,
			OBJECT_PT_XBModelToolsTexturePanel,
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