import bpy
import io
import math
import mathutils
import os
import traceback
import zlib
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

def import_wimdo(f, context):
	printProgress = context.scene.monado_forge_main.printProgress
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
	materials = []
	
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
		materialHeadersOffset = readAndParseInt(f,4)
		materialCount = readAndParseInt(f,4)
		materialUnknown1 = readAndParseInt(f,4)
		materialUnknown2 = readAndParseInt(f,4)
		materialExtraDataOffset = readAndParseInt(f,4)
		materialExtraDataCount = readAndParseInt(f,4)
		# a bunch of unknowns follow (looks likely to be offset+count pairs), skipping entirely for the moment
		f.seek(materialsOffset+materialHeadersOffset)
		for m in range(materialCount):
			matNameOffset = readAndParseInt(f,4)
			matFlags1 = readAndParseInt(f,4)
			matFlags2 = readAndParseInt(f,4)
			matBaseColour = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
			matU1 = readAndParseFloat(f)
			matTextureTableOffset = readAndParseInt(f,4)
			matTextureCount = readAndParseInt(f,4)
			matTextureMirrorFlags = readAndParseInt(f,4)
			matU2 = readAndParseInt(f,4)
			matU3 = readAndParseInt(f,4)
			matU4 = readAndParseInt(f,4)
			matU5 = readAndParseInt(f,4)
			matU6 = readAndParseInt(f,4)
			matExtraDataIndex = readAndParseInt(f,4)
			matU7 = readAndParseInt(f,4)
			matU8 = readAndParseInt(f,4)
			matU9 = readAndParseInt(f,4) # this is an offset
			matU10 = readAndParseInt(f,4)
			matU11 = readAndParseInt(f,4)
			matU12 = readAndParseInt(f,4)
			matU13 = readAndParseInt(f,4)
			matU14 = readAndParseInt(f,4)
			matU15 = readAndParseInt(f,4)
			matU16 = readAndParseInt(f,4)
			matU17 = readAndParseInt(f,4)
			matU18 = readAndParseInt(f,4)
			ftemp = f.tell()
			f.seek(materialsOffset+matNameOffset)
			matName = readStr(f)
			f.seek(materialsOffset+matTextureTableOffset)
			matTextureTable = []
			for t in range(matTextureCount):
				matTextureTable.append([readAndParseInt(f,2),readAndParseInt(f,2),readAndParseInt(f,2),readAndParseInt(f,2)])
			f.seek(ftemp)
			#materials.append([matName,matBaseColour,matTextureTable,matTextureMirrorFlags,matExtraDataIndex])
			mat = MonadoForgeWimdoMaterial(m)
			mat.setName(matName)
			mat.setBaseColour(matBaseColour)
			mat.setTextureTable(matTextureTable)
			mat.setTextureMirrorFlags(matTextureMirrorFlags)
			mat.setExtraDataIndex(matExtraDataIndex)
			materials.append(mat)
		f.seek(materialsOffset+materialExtraDataOffset)
		materialExtraData = []
		for mx in range(materialExtraDataCount):
			materialExtraData.append(readAndParseFloat(f))
		splitExtraData = []
		matCounter = -1
		nextStart = materials[0].getExtraDataIndex()
		for i,x in enumerate(materialExtraData):
			if i >= nextStart:
				splitExtraData.append([])
				if len(splitExtraData) < len(materials):
					nextStart = materials[len(splitExtraData)].getExtraDataIndex()
				else:
					nextStart = 10000000
			splitExtraData[-1].append(x)
		for i,sxd in enumerate(splitExtraData):
			materials[i].setExtraData(sxd)
		if printProgress:
			print("Found "+str(len(materials))+" materials.")
			#for m in materials:
			#	print(m.getName(),m.getBaseColour(),m.getTextureTable(),m.getTextureMirrorFlags(),m.getExtraDataIndex(),m.getExtraData())
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
	results = MonadoForgeWimdoPackage(skeleton,meshHeaders,shapeHeaders,materials)
	if printProgress:
		print("Finished parsing .wimdo file.")
	return results

def extract_wismt_subfile(f, headerOffset, headless=False):
	f.seek(headerOffset)
	compressedSize = readAndParseInt(f,4)
	uncompressedSize = readAndParseInt(f,4)
	dataOffset = readAndParseInt(f,4)
	f.seek(dataOffset)
	if headless:
		f.seek(headerOffset)
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
	filename = os.path.splitext(os.path.basename(f.name))[0]
	game = context.scene.monado_forge_main.game
	printProgress = context.scene.monado_forge_main.printProgress
	texPath = None
	if context.scene.monado_forge_import.autoSaveTextures:
		texPath = bpy.path.abspath(context.scene.monado_forge_import.texturePath)
	differentiate = context.scene.monado_forge_import.differentiateTextures
	splitTemps = context.scene.monado_forge_import.splitTemps
	listOfCachedTextureNames = [] # only needed for XC3 but no harm in building it regardless
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
	# the remaining subfiles (no matching content pointers) are just raw data to be used by the uncached textures (they don't even have headers)
	
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
	
	textureAlignment = {} # dict of {internal texture name : final name of image as it is in the Blender file}
	
	meshes = []
	vertexWeights = []
	nextSubfileIndex = 0
	hasRootSubfile = hasContentType[0] or hasContentType[1] or hasContentType[2]
	hasUncachedTexSubfile = hasContentType[3]
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
					if vertexTableOffset > 0: # not sure how we can have a mesh without vertexes, but just in case
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
						if len(weightTables) > 1:
							print_warning("You may need to use the Weight Table Override feature to get correct weights for some meshes.\nMake a new import for each table, and keep only the valid meshes.")
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
						print_warning("unknownVDTypes: "+str(unknownVDTypes))
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
							vertexWeights.append([vertexWeightData[weightVertTableIndex][v][0],vertexWeightData[weightVertTableIndex][v][1]])
					# we don't know how to pick the right weight table, so for now we let the user pick which one to use for all (needing multiple imports to do it right)
					forcedWeightTable = context.scene.monado_forge_import.tempWeightTableOverride
					if forcedWeightTable > 0:
						if forcedWeightTable >= len(weightTables):
							print_warning("weight table override too high, ignoring and treating as 0")
						else:
							totalOffset = weightTables[forcedWeightTable][0]
							vertexWeights = vertexWeights[totalOffset:]
					# we can "bake" the vertices with their weights now (but they keep the index in case it's more useful later)
					badWeightTable = False
					for i,vertices in vertexData.items():
						for v in vertices:
							weightIndex = v.getWeightSetIndex()
							if weightIndex == -1: continue
							try:
								for j in range(len(vertexWeights[weightIndex][0])):
									if vertexWeights[weightIndex][1][j] > 0:
										v.setWeight(vertexWeights[weightIndex][0][j],vertexWeights[weightIndex][1][j])
							except IndexError:
								badWeightTable = True
					if badWeightTable:
						print_warning("some vertices will not have weights due to the chosen weight table being too small")
					# now for the meshes themselves
					for md in wimdoResults.getMeshHeaders():
						vtIndex = md.getMeshVertTableIndex()
						ftIndex = md.getMeshFaceTableIndex()
						mtIndex = md.getMeshMaterialIndex()
						if vtIndex in unusedVertexTables:
							unusedVertexTables.remove(vtIndex)
						if ftIndex in unusedFaceTables:
							unusedFaceTables.remove(ftIndex)
						# this order of operations means that tables are still marked as "used" even if they're of dropped LODs
						if not context.scene.monado_forge_import.alsoImportLODs:
							if md.getMeshLODValue() > bestLOD:
								continue
						newMesh = MonadoForgeMesh()
						newMesh.setVertices(vertexData[vtIndex])
						newMesh.setFaces(faceData[ftIndex])
						newMesh.setWeightSets(vertexWeights)
						newMesh.setMaterialIndex(mtIndex)
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
							print_error("Bad cached texture (invalid subfilemagic); skipping "+str(textureName))
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
							sf.seek(textureOffset)
							listOfCachedTextureNames.append(textureName)
							dc = splitTemps and textureName.startswith("temp")
							nameToUse = textureName
							if differentiate:
								nameToUse = filename+"_"+nameToUse
							if context.scene.monado_forge_import.keepAllResolutions:
								nameToUse = os.path.join("res0",nameToUse)
							finalName = parse_texture(nameToUse,imgVersion,imgType,imgWidth,imgHeight,sf.read(textureFilesize),context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
							textureAlignment[textureName] = finalName
				finally:
					sf.close()
		del subfileData # just to ensure it's cleaned up as soon as possible
		nextSubfileIndex += 1
	if hasUncachedTexSubfile and context.scene.monado_forge_import.importUncachedTextures: # reminder: XC3 doesn't go in here at all (at least for most models)
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
						print_error("Bad uncached texture (invalid subfilemagic); skipping "+str(textureName))
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
						dc = splitTemps and textureName.startswith("temp")
						if context.scene.monado_forge_import.keepAllResolutions or highResSubfileIndex <= 0: # if there's no highResSubfileIndex, this is the best resolution
							sf.seek(0)
							nameToUse = textureName
							if differentiate:
								nameToUse = filename+"_"+nameToUse
							if context.scene.monado_forge_import.keepAllResolutions:
								nameToUse = os.path.join("res1",nameToUse)
							finalName = parse_texture(nameToUse,imgVersion,imgType,imgWidth,imgHeight,sf.read(),context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
							textureAlignment[textureName] = finalName
						# it is at this point where we need the data from the highest-resolution image
						if highResSubfileIndex > 0:
							hdfileHeaderOffset = mainOffset+subfileHeadersOffset+highResSubfileIndex*3*4
							hdfileName,hdfileData = extract_wismt_subfile(f,hdfileHeaderOffset)
							nameToUse = textureName
							if differentiate:
								nameToUse = filename+"_"+nameToUse
							if context.scene.monado_forge_import.keepAllResolutions:
								nameToUse = os.path.join("res2",nameToUse)
							finalName = parse_texture(nameToUse,imgVersion,imgType,imgWidth*2,imgHeight*2,hdfileData,context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
							textureAlignment[textureName] = finalName
				finally:
					sf.close()
		del subfileData
		nextSubfileIndex += 1
	# at this point, any remaining subfiles ought to be unheadered data, so ignore them
	# now, go fetch the external textures
	# assumption: the external .wismt files here are literally copy-pastes of the previous-game stuff
	# as in, the Ms have the typical headers, while the Hs are headerless and double the size
	# there's probably a way to reduce the copy-pasted code here, but the necessary differences are subtle
	texMPath = bpy.path.abspath(context.scene.monado_forge_import.textureRepoMPath)
	texHPath = bpy.path.abspath(context.scene.monado_forge_import.textureRepoHPath)
	if game == "XC3" and context.scene.monado_forge_import.importUncachedTextures and texMPath and texHPath:
		for textureName in set(listOfCachedTextureNames):
			mFilename = os.path.join(texMPath,textureName+".wismt")
			hFilename = os.path.join(texHPath,textureName+".wismt")
			if not os.path.exists(mFilename): continue
			hasH = os.path.exists(hFilename)
			with open(mFilename,"rb") as fM:
				subfileName,subfileData = extract_wismt_subfile(fM,0,headless=True)
				sf = io.BytesIO(subfileData)
				try: # no except, just finally (to close sf)
					sf.seek(len(subfileData)-0x4)
					submagic = sf.read(4)
					if submagic != b"LBIM":
						print_error("Bad uncached texture (invalid subfilemagic); skipping "+str(textureName))
						continue
					sf.seek(len(subfileData)-0x28)
					subfileUnknown5 = readAndParseInt(sf,4)
					subfileUnknown4 = readAndParseInt(sf,4)
					imgWidth = readAndParseInt(sf,4)
					imgHeight = readAndParseInt(sf,4)
					subfileUnknown3 = readAndParseInt(sf,4)
					subfileUnknown2 = readAndParseInt(sf,4)
					imgType = readAndParseInt(sf,4)
					subfileUnknown1 = readAndParseInt(sf,4)
					imgVersion = readAndParseInt(sf,4)
					dc = splitTemps and textureName.startswith("temp")
					if context.scene.monado_forge_import.keepAllResolutions or not hasH: # if there's no hasH, this is the best resolution
						sf.seek(0)
						nameToUse = textureName
						if differentiate:
							nameToUse = filename+"_"+nameToUse
						if context.scene.monado_forge_import.keepAllResolutions:
							nameToUse = os.path.join("res1",nameToUse)
						finalName = parse_texture(nameToUse,imgVersion,imgType,imgWidth,imgHeight,sf.read(),context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
						textureAlignment[textureName] = finalName
					# it is at this point where we need the data from the highest-resolution image
					if hasH:
						with open(hFilename,"rb") as fH:
							hdfileName,hdfileData = extract_wismt_subfile(fH,0,headless=True)
							nameToUse = textureName
							if differentiate:
								nameToUse = filename+"_"+nameToUse
							if context.scene.monado_forge_import.keepAllResolutions:
								nameToUse = os.path.join("res2",nameToUse)
							finalName = parse_texture(nameToUse,imgVersion,imgType,imgWidth*2,imgHeight*2,hdfileData,context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
							textureAlignment[textureName] = finalName
				finally:
					sf.close()
	
	# time to ready materials
	wimdoMaterials = wimdoResults.getMaterials()
	resultMaterials = []
	for mat in wimdoMaterials:
		newMat = MonadoForgeMaterial(mat.getIndex())
		newMat.setName(mat.getName())
		newMat.setBaseColour(mat.getBaseColour())
		newMat.setViewportColour(mat.getBaseColour())
		newMat.setExtraData(mat.getExtraData())
		# this is done in a way that "duplicates" texture references, but that's fairly harmless at this stage
		for ti,t in enumerate(mat.getTextureTable()):
			newTex = MonadoForgeTexture()
			texIndex = t[0] # ignore the unknowns for now
			newTex.setName(textureAlignment[textureHeaders[texIndex][3]])
			# need to figure out how to convert mirror flags into [x,y] format; until then, default [False,False]
			#newTex.setMirroring(mat.getTextureMirrorFlags())
			newMat.addTexture(newTex)
		resultMaterials.append(newMat)
	
	for m in meshes:
		m.indexVertices()
	
	results = MonadoForgeImportedPackage()
	results.addSkeleton(wimdoResults.getSkeleton())
	results.setMeshes(meshes)
	results.setMaterials(resultMaterials)
	if printProgress:
		print("Finished parsing .wismt file.")
	return results

def import_wimdo_only(self, context):
	absoluteDefsPath = bpy.path.abspath(context.scene.monado_forge_import.defsPath)
	if context.scene.monado_forge_main.printProgress:
		print("Importing model from: "+absoluteDefsPath)
	
	if os.path.splitext(absoluteDefsPath)[1] != ".wimdo":
		self.report({"ERROR"}, "File was not a .wimdo file")
		return {"CANCELLED"}
	
	with open(absoluteDefsPath, "rb") as f:
		forgeResults = import_wimdo(f, context)
	return realise_results(forgeResults, os.path.splitext(os.path.basename(absoluteDefsPath))[0], self, context)

def import_wimdo_and_wismt(self, context):
	absoluteDefsPath = bpy.path.abspath(context.scene.monado_forge_import.defsPath)
	absoluteDataPath = bpy.path.abspath(context.scene.monado_forge_import.dataPath)
	if context.scene.monado_forge_main.printProgress:
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
	printProgress = context.scene.monado_forge_main.printProgress
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
		boneSize = context.scene.monado_forge_import.boneSize
		positionEpsilon = context.scene.monado_forge_main.positionEpsilon
		angleEpsilon = context.scene.monado_forge_main.angleEpsilon
		armatures.append(create_armature_from_bones(boneList,armatureName,boneSize,positionEpsilon,angleEpsilon))
	# attach to the first armature created (this logic might change later)
	targetArmature = armatures[0]
	if printProgress:
		print("Finished creating "+str(len(armatures))+" armatures.")
	
	materials = forgeResults.getMaterials()
	newMatsByIndex = {}
	for m,mat in enumerate(materials):
		newMat = bpy.data.materials.new(name=mat.getName())
		newMat.diffuse_color = mat.getViewportColour()
		newMat.use_nodes = True # the default creation is "Principled BSDF" into "Material Output"
		n = newMat.node_tree.nodes
		bsdfNode = n.get("Principled BSDF")
		bsdfNode.inputs["Base Color"].default_value = mat.getViewportColour()
		for ti,t in enumerate(mat.getTextures()):
			texNode = n.new(type="ShaderNodeTexImage")
			texNode.extension = "EXTEND"
			texNode.image = bpy.data.images[t.getName()]
			texNode.location = [ti*250,0]
			# guess: the first texture is the base colour
			if ti == 0:
				newMat.node_tree.links.new(texNode.outputs["Color"],bsdfNode.inputs["Base Color"])
		for xi,x in enumerate(mat.getExtraData()):
			extraDataNode = n.new(type="ShaderNodeValue")
			extraDataNode.outputs["Value"].default_value = x
			extraDataNode.location = [xi*150,100]
		newMatsByIndex[mat.getIndex()] = newMat
	
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
			vertexesInEachSet = {}
			for i in weightIndexes:
				vertexesInEachSet[i] = mesh.getVertexesWithWeightIndex(i)
			weightSets = mesh.getWeightSets()
			for weightIndex in weightIndexes:
				try:
					weightSetData = weightSets[weightIndex]
				except IndexError: # can happen if the weight table override is high - the warning has already been given above
					continue
				for j in range(len(weightSetData[0])):
					groupIndex = weightSetData[0][j]
					groupValue = weightSetData[1][j]
					if groupValue == 0: continue
					vertexGroup = newMeshObject.vertex_groups[groupIndex]
					vertexesToAdd = vertexesInEachSet[weightIndex]
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
		meshData.materials.append(newMatsByIndex[mesh.getMaterialIndex()])
		if printProgress:
			print("Created mesh "+str(m)+".")
		
		# import complete, cleanup time
		#meshData.validate(verbose=True)
		meshData.validate()
		meshData.transform(mathutils.Euler((math.radians(90),0,0)).to_matrix().to_4x4(),shape_keys=True) # transform from lying down (+Y up +Z forward) to standing up (+Z up -Y forward)
		cleanup_mesh(context,newMeshObject,context.scene.monado_forge_import.cleanupLooseVertices,context.scene.monado_forge_import.cleanupEmptyGroups,context.scene.monado_forge_import.cleanupEmptyShapes)
		# attach mesh to armature
		armatureMod = newMeshObject.modifiers.new("Armature","ARMATURE")
		armatureMod.object = targetArmature
		newMeshObject.parent = targetArmature
	if printProgress:
		print("Finished creating "+str(len(meshes))+" meshes.")
	return {"FINISHED"}

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