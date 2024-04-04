import bpy
import io
import math
import mathutils
import os
import zlib

from . classes import *
from . utils import *
from . utils_img import *
from . import_funcs import *
from . modify_funcs import *

def import_sar1_skel_subfile(f, context):
	game = context.scene.monado_forge_main.game
	printProgress = context.scene.monado_forge_main.printProgress
	importEndpoints = context.scene.monado_forge_import.importEndpoints
	
	magic = f.read(4)
	if magic != b"1RAS":
		print_error(f.name+" is not a valid SAR1 file (unexpected header)")
		return None
	fileSize = readAndParseInt(f,4)
	version = readAndParseInt(f,4)
	numFiles = readAndParseInt(f,4)
	tocOffset = readAndParseInt(f,4)
	dataOffset = readAndParseInt(f,4)
	unknown1 = readAndParseInt(f,4)
	unknown2 = readAndParseInt(f,4)
	path = readStr(f)
	
	importedSkeletons = []
	for i in range(numFiles):
		f.seek(tocOffset+i*0x40)
		offset = readAndParseInt(f,4)
		size = readAndParseInt(f,4)
		unknown = readAndParseInt(f,4)
		filename = readStr(f)
		# todo: try to do this based on file type instead of name
		if game == "XC3":
			skelFilename = "skeleton"
		else: # XC2, XC1DE
			skelFilename = ".skl"
		if skelFilename not in filename: # yes, we're just dropping everything that's not a skeleton, we ain't lookin for them
			continue
		
		f.seek(offset)
		bcMagic = f.read(4)
		if bcMagic == b"LCHC": # some sort of special case I guess? (seen in XBC2ModelDecomp)
			continue
		if bcMagic != b"BC\x00\x00": # BC check
			print_error("BC check failed for "+filename+" (dunno what this means tbh, file probably bad in some way e.g. wrong endianness)")
			continue
		blockCount = readAndParseInt(f,4)
		fileSize = readAndParseInt(f,4)
		pointerCount = readAndParseInt(f,4)
		dataOffset = readAndParseInt(f,4)
		
		f.seek(offset+dataOffset+4)
		skelMagic = f.read(4)
		if skelMagic != b"SKEL":
			print_error(".skl file "+filename+" has bad header")
			return None
		
		skelHeaderUnknown1 = readAndParseInt(f,4)
		skelHeaderUnknown2 = readAndParseInt(f,4)
		skelTocItems = []
		for j in range(10): # yeah it's a magic number, deal with it
			itemOffset = readAndParseInt(f,4)
			itemUnknown1 = readAndParseInt(f,4)
			itemCount = readAndParseInt(f,4)
			itemUnknown2 = readAndParseInt(f,4)
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
			print_error(".skl file "+filename+" has inconsistent bone counts (see console)")
			return None
		if importEndpoints:
			if (skelTocItems[6][2] != skelTocItems[7][2]) or (skelTocItems[7][2] != skelTocItems[8][2]):
				print("endpoint parent entries: "+str(skelTocItems[6][2]))
				print("endpoint name entries: "+str(skelTocItems[7][2]))
				print("endpoint data entries: "+str(skelTocItems[8][2]))
				print_warning(".skl file "+filename+" has inconsistent endpoint counts (see console); endpoint import skipped")
		forgeBones = []
		for b in range(skelTocItems[2][2]):
			# parent
			f.seek(offset+skelTocItems[2][0]+b*2)
			parent = readAndParseInt(f,2,signed=True)
			# name
			f.seek(offset+skelTocItems[3][0]+b*16)
			nameOffset = readAndParseInt(f,4)
			f.seek(offset+nameOffset)
			name = readStr(f)
			# data
			f.seek(offset+skelTocItems[4][0]+b*(4*12))
			px = readAndParseFloat(f)
			py = readAndParseFloat(f)
			pz = readAndParseFloat(f)
			pw = readAndParseFloat(f)
			rx = readAndParseFloat(f)
			ry = readAndParseFloat(f)
			rz = readAndParseFloat(f)
			rw = readAndParseFloat(f)
			sx = readAndParseFloat(f)
			sy = readAndParseFloat(f)
			sz = readAndParseFloat(f)
			sw = readAndParseFloat(f)
			# reminder that the pos and scale are x,y,z,w but the rotation is w,x,y,z
			fb = MonadoForgeBone(len(forgeBones))
			fb.name = name
			fb.parent = parent
			fb.position = [px,py,pz,pw]
			fb.rotation = [rw,rx,ry,rz]
			fb.scale = [sx,sy,sz,sw]
			fb.isEndpoint = False
			forgeBones.append(fb)
		if importEndpoints:
			for ep in range(skelTocItems[6][2]):
				# parent
				f.seek(offset+skelTocItems[6][0]+ep*2)
				parent = readAndParseInt(f,2,signed=True)
				# name
				f.seek(offset+skelTocItems[7][0]+ep*8) # yeah endpoint names are packed tighter than "normal" bone names
				nameOffset = readAndParseInt(f,4)
				f.seek(offset+nameOffset)
				name = readStr(f)
				# data
				f.seek(offset+skelTocItems[8][0]+ep*(4*12))
				px = readAndParseFloat(f)
				py = readAndParseFloat(f)
				pz = readAndParseFloat(f)
				pw = readAndParseFloat(f)
				rx = readAndParseFloat(f)
				ry = readAndParseFloat(f)
				rz = readAndParseFloat(f)
				rw = readAndParseFloat(f)
				sx = readAndParseFloat(f)
				sy = readAndParseFloat(f)
				sz = readAndParseFloat(f)
				sw = readAndParseFloat(f)
				# for some reason, endpoints tend to have pw = 0, which positions it relative to root instead of parent (and we don't want that)
				if pw == 0.0: pw = 1.0
				# reminder that the pos and scale are x,y,z,w but the rotation is w,x,y,z
				fb = MonadoForgeBone(len(forgeBones))
				fb.name = name
				fb.parent = parent
				fb.position = [px,py,pz,pw]
				fb.rotation = [rw,rx,ry,rz]
				fb.scale = [sx,sy,sz,sw]
				fb.isEndpoint = True
				forgeBones.append(fb)
		if printProgress:
			print("Read "+str(len(forgeBones))+" bones.")
		importedSkeletons.append(forgeBones)
	if not importedSkeletons:
		print_error("No valid .skl items found in file")
		return None
	# assumption: there can only ever be a single skeleton in a file
	# so why are we making a list? it'll be easier to pivot in the future if a counterexample is found
	if len(importedSkeletons) > 1:
		print_warning(".skl file has multiple skeletons; returning only the first (please report this issue)")
	skeleton = MonadoForgeSkeleton()
	skeleton.bones = importedSkeletons[0]
	return skeleton

def import_wimdo(f, context, externalSkeleton=None):
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
					meshFlags1 = readAndParseInt(f,2)
					meshFlags2 = readAndParseInt(f,2)
					meshVertTableIndex = readAndParseInt(f,2)
					meshFaceTableIndex = readAndParseInt(f,2)
					f.seek(f.tell()+2) # skip unknown
					meshMaterialIndex = readAndParseInt(f,2)
					f.seek(f.tell()+14) # skip unknown
					meshLODValue = readAndParseInt(f,2)
					f.seek(f.tell()+16) # skip unknown
					meshHeaders.append(MonadoForgeMeshHeader(meshID,meshFlags1,meshFlags2,meshVertTableIndex,meshFaceTableIndex,meshMaterialIndex,meshLODValue))
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
				fb = MonadoForgeBone(len(forgeBones))
				fb.name = boneName
				fb.position = bonePosition[:] # the [:] is because we're turning a Vector into a list
				fb.rotation = rotMatrix.to_quaternion()
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
	
	if materialsOffset > 0 and not context.scene.monado_forge_import.skipMaterialImport:
		f.seek(materialsOffset)
		materialHeadersOffset = readAndParseInt(f,4)
		materialCount = readAndParseInt(f,4)
		materialUnknown1 = readAndParseInt(f,4)
		materialUnknown2 = readAndParseInt(f,4)
		materialExtraDataOffset = readAndParseInt(f,4)
		materialExtraDataCount = readAndParseInt(f,4)
		# a bunch of unknowns follow (looks likely to be offset+count pairs), skipping entirely for the moment
		f.seek(materialsOffset+92) # a magic number unfortunately
		samplerTableOffset = readAndParseInt(f,4)
		# get the samplers now so we can put them in the materials
		f.seek(materialsOffset+samplerTableOffset)
		samplerCount = readAndParseInt(f,4)
		samplerOffset = readAndParseInt(f,4)
		f.seek(materialsOffset+samplerTableOffset+samplerOffset)
		samplers = []
		for s in range(samplerCount):
			samplers.append([readAndParseInt(f,4),readAndParseFloat(f)]) # flags, LOD bias (don't need to parse/understand here)
		f.seek(materialsOffset+materialHeadersOffset)
		for m in range(materialCount):
			matNameOffset = readAndParseInt(f,4)
			matFlags1 = readAndParseInt(f,4)
			matFlags2 = readAndParseInt(f,4)
			matBaseColour = [readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f),readAndParseFloat(f)]
			matU0 = readAndParseFloat(f)
			matTextureTableOffset = readAndParseInt(f,4)
			matTextureCount = readAndParseInt(f,4)
			matU1 = readAndParseInt(f,4) # some sort of flags, probably
			matU2 = readAndParseInt(f,4)
			matU3 = readAndParseInt(f,4)
			matU4 = readAndParseInt(f,4)
			matU5 = readAndParseInt(f,4)
			matU6 = readAndParseInt(f,4)
			matExtraDataIndex = readAndParseInt(f,4)
			matU7 = readAndParseInt(f,4)
			matU8 = readAndParseInt(f,4)
			matU9 = readAndParseInt(f,4) # this is an offset that we need later
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
			f.seek(materialsOffset+matU9+4)
			renderPassType = readAndParseInt(f,2)
			f.seek(ftemp)
			#materials.append([matName,matBaseColour,matTextureTable,matExtraDataIndex])
			mat = MonadoForgeWimdoMaterial(m)
			mat.name = matName
			mat.baseColour = matBaseColour
			mat.textureTable = matTextureTable
			mat.samplers = samplers # yes this means each material has the samplers duplicated, but that's not really a big deal (it's two numbers)
			mat.extraDataIndex = matExtraDataIndex
			mat.renderPassType = renderPassType
			materials.append(mat)
		f.seek(materialsOffset+materialExtraDataOffset)
		materialExtraData = []
		for mx in range(materialExtraDataCount):
			materialExtraData.append(readAndParseFloat(f))
		splitExtraData = []
		matCounter = -1
		nextStart = materials[0].extraDataIndex
		for i,x in enumerate(materialExtraData):
			if i >= nextStart:
				splitExtraData.append([])
				if len(splitExtraData) < len(materials):
					nextStart = materials[len(splitExtraData)].extraDataIndex
				else:
					nextStart = 10000000
			splitExtraData[-1].append(x)
		for i,sxd in enumerate(splitExtraData):
			materials[i].extraData = sxd
		if printProgress:
			print("Found "+str(len(materials))+" materials.")
	if vertexBufferOffset > 0:
		f.seek(vertexBufferOffset)
	if shadersOffset > 0:
		f.seek(shadersOffset)
	if cachedTexturesTableOffset > 0:
		f.seek(cachedTexturesTableOffset)
	if uncachedTexturesTableOffset > 0: # don't need this for the texture files themselves - it's for metadata (alpha, repeat, etc)
		f.seek(uncachedTexturesTableOffset)
	
	skeleton = MonadoForgeSkeleton()
	skeleton.bones = forgeBones
	results = MonadoForgeWimdoPackage(skeleton,externalSkeleton,meshHeaders,shapeHeaders,materials)
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
	if textureIDsOffset > 0 and not context.scene.monado_forge_import.skipMaterialImport:
		f.seek(mainOffset+textureIDsOffset)
		for i in range(textureIDsCount):
			textureIDList.append(readAndParseInt(f,2))
	textureHeaders = []
	if textureCountOffset > 0 and not context.scene.monado_forge_import.skipMaterialImport:
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
	maxColourLayers = 0 # materials will need to know this without knowing what meshes they're on
	maxUVLayers = 0 # same
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
					weightTableIndexConversion = []
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
						weightTableLodCount = readAndParseInt(sf,2)
						weightTableLodOffset = readAndParseInt(sf,4)
						sf.seek(weightTableOffset)
						for i in range(weightTableCount):
							# buncha unknowns in here, might not use it necessarily
							wtStartIndex = readAndParseInt(sf,4)
							wtDataOffset = readAndParseInt(sf,4)
							wtDataCount = readAndParseInt(sf,4)
							sf.seek(sf.tell()+17)
							wtLOD = readAndParseInt(sf,1)
							sf.seek(sf.tell()+10)
							weightTables.append([wtStartIndex,wtDataOffset,wtDataCount,wtLOD])
						sf.seek(weightTableLodOffset)
						for i in range(weightTableLodCount):
							weightTableIndexConversion.append([])
							for j in range(9): # apparently this is fixed (https://github.com/atnavon/xc2f/wiki/Geometry)
								weightTableIndexConversion[-1].append(readAndParseInt(sf,2)-1) # doing a -1 here for easier debugging later
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
						vertexData[i] = MonadoForgeVertexList()
						vertexWeightData[i] = []
						vtDataOffset,vtDataCount,vtBlockSize,vtDescOffset,vtDescCount,vertexDescriptors = vertexTables[i]
						sf.seek(dataOffset+vtDataOffset)
						for vIndex in range(vtDataCount):
							newVertex = MonadoForgeVertex(vIndex)
							weightVertex = [[],[]]
							hasColourLayers = [False] # only one colour layer is known at this time
							hasUVLayers = [False,False,False]
							for vd in vertexDescriptors:
								vdType,vdSize = vd
								if vdType == 0: # position
									newVertex.position = [readAndParseFloat(sf),readAndParseFloat(sf),readAndParseFloat(sf)]
								elif vdType == 3: # weights index
									newVertex.weightSetIndex = readAndParseInt(sf,4)
								elif vdType == 5: # UV 1 (inverted Y reminder) (yes this is copy/pasted for other layers but this is kind of easier actually)
									newVertex.setUV(0,[readAndParseFloat(sf),1.0-readAndParseFloat(sf)])
									hasUVLayers[0] = True
								elif vdType == 6: # UV 2
									newVertex.setUV(1,[readAndParseFloat(sf),1.0-readAndParseFloat(sf)])
									hasUVLayers[1] = True
								elif vdType == 7: # UV 3
									newVertex.setUV(2,[readAndParseFloat(sf),1.0-readAndParseFloat(sf)])
									hasUVLayers[2] = True
								elif vdType == 17: # colour 1
									a,r,g,b = readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1)
									newVertex.setColour(0,[r,g,b,a])
									hasColourLayers[0] = True
								elif vdType == 28: # normals
									newNormal = [readAndParseInt(sf,1,signed=True)/128.0,readAndParseInt(sf,1,signed=True)/128.0,readAndParseInt(sf,1,signed=True)/128.0]
									readAndParseInt(sf,1,signed=True) # dummy
									# doesn't necessarily read as normalized
									newVertex.normal = mathutils.Vector(newNormal).normalized()[:]
								elif vdType == 41: # weight values (weightTable verts only)
									weightVertex[1] = [readAndParseInt(sf,2)/65535.0,readAndParseInt(sf,2)/65535.0,readAndParseInt(sf,2)/65535.0,readAndParseInt(sf,2)/65535.0]
								elif vdType == 42: # weight IDs (weightTable verts only)
									weightVertex[0] = [readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1),readAndParseInt(sf,1)]
								else:
									unknownVDTypes[vdType] = vdSize
									sf.seek(sf.tell()+vdSize)
							vertexData[i].addVertex(vIndex,newVertex,automerge=True)
							vertexWeightData[i].append(weightVertex)
							maxColourLayers = max(maxColourLayers,sum(hasColourLayers))
							maxUVLayers = max(maxUVLayers,sum(hasUVLayers))
					if printProgress and vertexData != {}:
						print("Finished reading vertex data.")
					if unknownVDTypes:
						print_warning("unknownVDTypes: "+str(unknownVDTypes))
					for i in range(len(faceTables)):
						faceData[i] = []
						ftDataOffset,ftVertCount,ftVertexes = faceTables[i]
						for j in range(0,len(ftVertexes),3):
							newFaceIndex = len(faceData[i])
							newFace = MonadoForgeFace(newFaceIndex)
							newFace.vertexIndexes = [ftVertexes[j],ftVertexes[j+1],ftVertexes[j+2]]
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
							vertexBeingModified.position = [readAndParseFloat(sf),readAndParseFloat(sf),readAndParseFloat(sf)]
							newNormal = [(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1]
							# doesn't necessarily read as normalized
							vertexBeingModified.normal = mathutils.Vector(newNormal).normalized()[:]
							sf.seek(sf.tell()+targetBlockSize-15) # the magic -15 is the length of the position+normal (4*3 + 3)
						shapeNameList = ["basis"] + [h[0] for h in wimdoResults.shapeHeaders] # "basis" needs to be added because the first target is also the base shape for some reason
						for j in range(shapeTargetCounts+1):
							if j == 0: continue # as above, the first is the basis so we don't need it
							# it's okay to overwrite these variables, we don't need the above ones anymore
							targetDataChunkOffset,targetVertexCount,targetBlockSize,targetUnknown,targetType = shapeTargets[shapeTargetIndex+j+1]
							sf.seek(dataOffset+targetDataChunkOffset)
							newShape = MonadoForgeMeshShape()
							for k in range(targetVertexCount):
								newPosition = [readAndParseFloat(sf),readAndParseFloat(sf),readAndParseFloat(sf)]
								readAndParseInt(sf,4) # dummy
								newNormal = [(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1,(readAndParseInt(sf,1)/255.0)*2-1]
								readAndParseInt(sf,1) # more dummies
								readAndParseInt(sf,4)
								readAndParseInt(sf,4)
								index = readAndParseInt(sf,4)
								newVertex = MonadoForgeVertex(index)
								newVertex.position = newPosition
								# doesn't necessarily read as normalized
								newVertex.normal = mathutils.Vector(newNormal).normalized()[:]
								newShape.setVertex(index,newVertex)
							newShape.vertexTableIndex = shapeDataChunkID
							newShape.name = shapeNameList[j] # probably wrong but need to find a counterexample
							shapes.append(newShape)
					if printProgress and shapes != []:
						print("Finished reading shape data.")
					shapesByVertexTableIndex = {}
					for s in shapes:
						thisShapesIndex = s.vertexTableIndex
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
					# split up the weight list by weight table
					splitVertexWeights = {}
					for splitTableIndex in range(len(weightTables)):
						startIndex = weightTables[splitTableIndex][1]-weightTables[splitTableIndex][0]
						endIndex = weightTables[splitTableIndex][1]+weightTables[splitTableIndex][2]
						splitVertexWeights[splitTableIndex] = vertexWeights[startIndex:endIndex]
					# now for the meshes themselves
					for md in wimdoResults.meshHeaders:
						vtIndex = md.meshVertTableIndex
						ftIndex = md.meshFaceTableIndex
						mtIndex = md.meshMaterialIndex
						
						# here is where we can determine the necessary weight table for this mesh
						# this is entirely based on what xc3_lib does (no further trying to understand it has been done)
						flags1 = md.meshFlags1
						meshLod = md.meshLODValue
						tableID = 0
						if flags1 == 64:
							tableID = 4
						else:
							passLookup = {0:0,1:1,7:3}
							passType = wimdoResults.materials[mtIndex].renderPassType
							try:
								tableID = passLookup[passType]
							except KeyError:
								print_warning("unknown passType:",passType)
								tableID = 0
						finalTableID = weightTableIndexConversion[meshLod-1][tableID]
						if finalTableID == -1:
							print_warning("bad finalTableID")
							finalTableID = 0
						
						if vtIndex in unusedVertexTables:
							unusedVertexTables.remove(vtIndex)
						if ftIndex in unusedFaceTables:
							unusedFaceTables.remove(ftIndex)
						# this order of operations means that tables are still marked as "used" even if they're of dropped LODs
						if not context.scene.monado_forge_import.alsoImportLODs:
							if md.meshLODValue > bestLOD:
								continue
						
						newMesh = MonadoForgeMesh()
						newMesh.vertices = vertexData[vtIndex]
						newMesh.faces = faceData[ftIndex]
						newMesh.weightSets = splitVertexWeights[finalTableID]
						newMesh.materialIndex = mtIndex
						if vtIndex in shapesByVertexTableIndex.keys():
							newMesh.shapes = shapesByVertexTableIndex[vtIndex]
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
			if contentType == 2 and not context.scene.monado_forge_import.skipMaterialImport: # cached texture
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
							finalName = parse_texture_wismt(nameToUse,imgVersion,imgType,imgWidth,imgHeight,sf.read(textureFilesize),context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
							textureAlignment[textureName] = finalName
				finally:
					sf.close()
		del subfileData # just to ensure it's cleaned up as soon as possible
		nextSubfileIndex += 1
	# reminder: XC3 doesn't go in here at all (at least for most models)
	if hasUncachedTexSubfile and context.scene.monado_forge_import.importUncachedTextures and not context.scene.monado_forge_import.skipMaterialImport:
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
							finalName = parse_texture_wismt(nameToUse,imgVersion,imgType,imgWidth,imgHeight,sf.read(),context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
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
							finalName = parse_texture_wismt(nameToUse,imgVersion,imgType,imgWidth*2,imgHeight*2,hdfileData,context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
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
	if game == "XC3" and context.scene.monado_forge_import.importUncachedTextures and not context.scene.monado_forge_import.skipMaterialImport and texMPath and texHPath:
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
						finalName = parse_texture_wismt(nameToUse,imgVersion,imgType,imgWidth,imgHeight,sf.read(),context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
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
							finalName = parse_texture_wismt(nameToUse,imgVersion,imgType,imgWidth*2,imgHeight*2,hdfileData,context.scene.monado_forge_import.blueBC5,printProgress,saveTo=texPath,dechannelise=dc)
							textureAlignment[textureName] = finalName
				finally:
					sf.close()
	
	# time to ready materials
	wimdoMaterials = wimdoResults.materials
	resultMaterials = []
	for mat in wimdoMaterials:
		newMat = MonadoForgeMaterial(mat.index)
		newMat.name = mat.name
		newMat.baseColour = mat.baseColour
		newMat.viewportColour = mat.baseColour
		newMat.extraData = mat.extraData
		newMat.colourLayerCount = maxColourLayers
		newMat.uvLayerCount = maxUVLayers
		matSamplers = mat.samplers
		# this is done in a way that "duplicates" texture references, but that's fairly harmless at this stage
		for ti,t in enumerate(mat.textureTable):
			newTex = MonadoForgeTexture()
			texIndex = t[0] # ignore the unknowns for now
			newTex.name = textureAlignment[textureHeaders[texIndex][3]]
			texSampler = matSamplers[t[1]]
			samplerFlags = texSampler[0]
			# the known sampler flags:
			# 0x01 = u-repeat
			# 0x02 = v-repeat
			# 0x04 = u-mirror
			# 0x08 = v-mirror
			# 0x10 = no filtering (use nearest instead of linear)
			# 0x20 = set UVW to clamped (override)
			# 0x40 = disable mipmaps
			# 0x80 = set UVW to repeat (override)
			# the current code skips the mipmaps and UVW overrides (since we don't support 3D textures yet anyways)
			uRepeat = (samplerFlags & 0x01) != 0
			vRepeat = (samplerFlags & 0x02) != 0
			uMirror = (samplerFlags & 0x04) != 0
			vMirror = (samplerFlags & 0x08) != 0
			noFiltering = (samplerFlags & 0x10) != 0
			newTex.repeating = [uRepeat,vRepeat]
			newTex.mirroring = [uMirror,vMirror]
			newTex.isFiltered = not noFiltering # yes we're flipping the meaning, "true means don't" is confusing
			newMat.addTexture(newTex)
		resultMaterials.append(newMat)
	
	results = MonadoForgeImportedPackage()
	results.skeleton = wimdoResults.skeleton
	results.externalSkeleton = wimdoResults.externalSkeleton
	results.meshes = meshes
	results.materials = resultMaterials
	if printProgress:
		print("Finished parsing .wismt file.")
	return results

def import_sar1_skeleton_only(self, context):
	absolutePath = bpy.path.abspath(context.scene.monado_forge_import.skeletonPath)
	boneSize = context.scene.monado_forge_import.boneSize
	positionEpsilon = context.scene.monado_forge_main.positionEpsilon
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
	
	with open(absolutePath, "rb") as f:
		skeleton = import_sar1_skel_subfile(f, context)
	
	# we now have the skeleton in generic format - create the armature
	armatureName = skeleton.bones[0].name
	if armatureName.endswith("_top"):
		armatureName = armatureName[:-4]
	if armatureName.endswith("_Bone"):
		armatureName = armatureName[:-5]
	if context.scene.monado_forge_import.importToCursor:
		pos = context.scene.cursor.location
		rot = context.scene.cursor.rotation_euler
	else:
		pos = (0,0,0)
		rot = (0,0,0)
	create_armature_from_bones(skeleton,armatureName,pos,rot,boneSize,positionEpsilon,angleEpsilon)
	return {"FINISHED"}

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

def import_sar1_skel_and_wimdo_and_wismt(self, context):
	absoluteSkelPath = bpy.path.abspath(context.scene.monado_forge_import.skeletonPath)
	absoluteDefsPath = bpy.path.abspath(context.scene.monado_forge_import.defsPath)
	absoluteDataPath = bpy.path.abspath(context.scene.monado_forge_import.dataPath)
	if context.scene.monado_forge_main.printProgress:
		print("Importing model from: "+absoluteSkelPath+" & "+absoluteDefsPath+" & "+absoluteDataPath)
	
	# will check skel file validity later
	if os.path.splitext(absoluteDefsPath)[1] != ".wimdo":
		self.report({"ERROR"}, "Second file was not a .wimdo file")
		return {"CANCELLED"}
	if os.path.splitext(absoluteDataPath)[1] != ".wismt":
		self.report({"ERROR"}, "Third file was not a .wismt file")
		return {"CANCELLED"}
	
	# we can't actually use the .arc/.chr in the .wimdo/.wismt importing (since everything's based on the indices of the internal bones)
	# thus, we just do a merge into it after the fact
	with open(absoluteSkelPath, "rb") as f:
		skelResult = import_sar1_skel_subfile(f, context)
	with open(absoluteDefsPath, "rb") as f:
		wimdoResults = import_wimdo(f, context, externalSkeleton=skelResult)
	with open(absoluteDataPath, "rb") as f:
		wismtResults = import_wismt(f, wimdoResults, context)
	return realise_results(wismtResults, os.path.splitext(os.path.basename(absoluteDataPath))[0], self, context)

def register():
	pass

def unregister():
	pass

#[...]