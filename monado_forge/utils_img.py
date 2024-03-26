import bpy
import io
import math
import mathutils
import numpy
import os
import struct
from contextlib import redirect_stdout

from . classes import *
from . utils import *

# https://wiki.tockdom.com/wiki/Image_Formats
# [formatName, bitsPerPixel, blockWidth, blockHeight, blockBytesize]
brresImageFormats = {
						 0:["I4",4,8,8,32],
						 1:["I8",8,8,4,32],
						 2:["IA4",8,8,4,32],
						 3:["IA8",16,4,4,32],
						 4:["RGB565",16,4,4,32], # aka R5G6B5
						 5:["RGB5A3",16,4,4,32], # aka R5G5B5A3
						 6:["RGBA32",32,4,4,64], # aka RGBA8
						 8:["C4",4,8,8,32], # aka CI4
						 9:["C8",8,8,4,32], # aka CI8
						10:["C14X2",16,4,4,32], # aka CI14x2
						14:["CMPR",4,8,8,32], # this is BC1_UNORM with 2x2 sub-blocks, aka DXT1
					}

# much of this was copied from parse_texture_wismt (it seems hard to try and merge the two)
def parse_texture_brres(textureName,imgType,imgWidth,imgHeight,rawData,palette,printProgress,overwrite=True,saveTo=None,dechannelise=False):
	if imgType > 0xe:
		print_error(textureName+" is of an unknown/unsupported image type (id "+str(imgType)+")")
		return
	if imgType in [8,9,10] and not palette:
		print_error(textureName+" uses a palette format but no palette was provided")
		return
	imgFormat,bitsPerPixel,blockWidth,blockHeight,blockBytesize = brresImageFormats[imgType]
	
	# first, check to see if image of the intended name exists already, and how to proceed
	try:
		existingImage = bpy.data.images[textureName]
		if overwrite:
			bpy.data.images.remove(existingImage)
	except KeyError as e: # no existing image of the same name
		pass # fine, move on
	newImage = bpy.data.images.new(textureName,imgWidth,imgHeight,alpha=True)
	# don't really want to do any of this until the end, but apparently setting the filepath after setting the pixels clears the image for no good reason
	newImage.file_format = "PNG"
	if saveTo:
		newImage.filepath = os.path.join(saveTo,textureName+".png")
	
	# images must be divisible by the block size - extend them as necessary
	virtImgWidth = imgWidth if imgWidth % blockWidth == 0 else imgWidth + (blockWidth - (imgWidth % blockWidth))
	virtImgHeight = imgHeight if imgHeight % blockHeight == 0 else imgHeight + (blockHeight - (imgHeight % blockHeight))
	# gotta create the image in full emptiness to start with, so we can random-access-fill the blocks as they come
	# Blender always needs alpha, so colours must be length 4
	pixels = numpy.zeros([virtImgHeight*virtImgWidth,4],dtype=numpy.float32)
	
	blockCountX = virtImgWidth // blockWidth
	blockCountY = virtImgHeight // blockHeight
	blockCount = blockCountX*blockCountY
	
	d = io.BytesIO(rawData)
	
	for block in range(blockCount):
		if printProgress and block % 64 == 0: # printing for every single b racks up the import time a lot (e.g. 12s to 20s)
			print_progress_bar(block,blockCount,textureName)
		for block2 in range(blockWidth):
			targetBlock = block*blockWidth + block2
			if targetBlock >= blockCount: continue # can happen for tiny textures, not a problem
			targetBlockX = targetBlock % blockCountX
			targetBlockY = targetBlock // blockCountX
			subBlocks = 4 if imgFormat == "CMPR" else 1
			for sb in range(subBlocks): # sub-blocks, if necessary
				# convert block to pixel (Y is inverted, X is not)
				blockRootPixelX = targetBlockX*blockWidth + (4 if (subBlocks>1 and sb%2==1) else 0)
				blockRootPixelY = virtImgHeight - targetBlockY*blockHeight - blockHeight + (4 if (subBlocks>1 and sb <=1) else 0)
				if imgFormat == "CMPR": # mostly copy-pasted form the BC1 section in parse_texture_wismt
					endpoint0 = readAndParseIntBig(d,2)
					endpoint1 = readAndParseIntBig(d,2)
					row0 = readAndParseIntBig(d,1)
					row1 = readAndParseIntBig(d,1)
					row2 = readAndParseIntBig(d,1)
					row3 = readAndParseIntBig(d,1)
					r0,g0,b0 = ((endpoint0 & 0b1111100000000000) >> 11),((endpoint0 & 0b0000011111100000) >> 5),(endpoint0 & 0b0000000000011111)
					r1,g1,b1 = ((endpoint1 & 0b1111100000000000) >> 11),((endpoint1 & 0b0000011111100000) >> 5),(endpoint1 & 0b0000000000011111)
					# potential future feature: autodetect images that are supposed to be greyscale and only use the higher-resolution green channel
					#if monochrome and not(r0 == b0 and r1 == b1 and abs(r0*2 - g0) <= 1 and abs(r1*2 - g1) <= 1):
					#	monochrome = False
					colours = [[],[],[],[]]
					colours[0] = [r0/0b11111,g0/0b111111,b0/0b11111,1.0]
					colours[1] = [r1/0b11111,g1/0b111111,b1/0b11111,1.0]
					if endpoint0 > endpoint1:
						colours[2] = [2/3*colours[0][0]+1/3*colours[1][0],2/3*colours[0][1]+1/3*colours[1][1],2/3*colours[0][2]+1/3*colours[1][2],1.0]
						colours[3] = [1/3*colours[0][0]+2/3*colours[1][0],1/3*colours[0][1]+2/3*colours[1][1],1/3*colours[0][2]+2/3*colours[1][2],1.0]
					else:
						colours[2] = [1/2*colours[0][0]+1/2*colours[1][0],1/2*colours[0][1]+1/2*colours[1][1],1/2*colours[0][2]+1/2*colours[1][2],1.0]
						colours[3] = [0.0,0.0,0.0,0.0] # binary alpha
					# the X-position of pixels in blocks is inverted compared to wismt
					pixelIndexes = [
									(row3 & 0b11000000) >> 6, (row3 & 0b00110000) >> 4, (row3 & 0b00001100) >> 2, (row3 & 0b00000011),
									(row2 & 0b11000000) >> 6, (row2 & 0b00110000) >> 4, (row2 & 0b00001100) >> 2, (row2 & 0b00000011),
									(row1 & 0b11000000) >> 6, (row1 & 0b00110000) >> 4, (row1 & 0b00001100) >> 2, (row1 & 0b00000011),
									(row0 & 0b11000000) >> 6, (row0 & 0b00110000) >> 4, (row0 & 0b00001100) >> 2, (row0 & 0b00000011),
									]
					for p,pi in enumerate(pixelIndexes):
						pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = colours[pi]
				elif imgFormat == "RGBA32":
					chunkAR = [readAndParseIntBig(d,1) for x in range(blockBytesize//2)]
					chunkGB = [readAndParseIntBig(d,1) for x in range(blockBytesize//2)]
					chunkA = chunkAR[::2]
					chunkR = chunkAR[1::2]
					chunkG = chunkGB[::2]
					chunkB = chunkGB[1::2]
					colours = []
					for c in range(len(chunkA)):
						colours.append([chunkR[c],chunkG[c],chunkB[c],chunkA[c]])
					blockedColours = [
										colours[12],colours[13],colours[14],colours[15],
										colours[ 8],colours[ 9],colours[10],colours[11],
										colours[ 4],colours[ 5],colours[ 6],colours[ 7],
										colours[ 0],colours[ 1],colours[ 2],colours[ 3],
										]
					for p,pv in enumerate(blockedColours):
						pixels[(blockRootPixelX + p % blockWidth) + ((blockRootPixelY + p // blockWidth) * virtImgWidth)] = [x/255 for x in pv]
				else: # every other format can be done fairly similarly
					data = d.read(blockBytesize)
					br = BitReader(data)
					rowData = [] # using numpy for this seems to be slower? guessing there's too much churn in these small loops
					for row in range(blockHeight):
						rowData.append([])
						for col in range(blockWidth):
							if imgFormat == "I4":
								rowData[-1].append([br.readbits(4) * 0x11]*3+[255]) # reminder: [read(x)]*3 results in [v,v,v], not [read(x),read(x),read(x)]
							elif imgFormat == "I8":
								rowData[-1].append([br.readbits(8)]*3+[255])
							elif imgFormat == "IA4":
								alpha = br.readbits(4)
								value = br.readbits(4)
								rowData[-1].append([value * 0x11]*3+[alpha])
							elif imgFormat == "IA8":
								alpha = br.readbits(8)
								value = br.readbits(8)
								rowData[-1].append([value]*3+[alpha])
							elif imgFormat == "RGB565":
								r = br.readbits(5)/31*255
								g = br.readbits(6)/63*255
								b = br.readbits(5)/31*255
								rowData[-1].append([r,g,b,255])
							elif imgFormat == "RGB5A3":
								mode = br.readbits(1)
								if mode:
									a = 255
									r = br.readbits(5)/31*255
									g = br.readbits(5)/31*255
									b = br.readbits(5)/31*255
								else:
									a = br.readbits(3)/7*255
									r = br.readbits(4)/15*255
									g = br.readbits(4)/15*255
									b = br.readbits(4)/15*255
								rowData[-1].append([r,g,b,a])
							elif imgFormat == "C4":
								rowData[-1].append(palette[br.readbits(4)])
							elif imgFormat == "C8":
								rowData[-1].append(palette[br.readbits(8)])
							elif imgFormat == "C14X2":
								waste = br.readbits(2)
								rowData[-1].append(palette[br.readbits(14)])
						pixelValues = list(reversed(rowData))
						for p,pv in enumerate(flattened_list(pixelValues)):
							pixels[(blockRootPixelX + p % blockWidth) + ((blockRootPixelY + p // blockWidth) * virtImgWidth)] = [x/255 for x in pv]
	if printProgress:
		print_progress_bar(blockCount,blockCount,textureName)
	d.close()
	
	finalImages = [[newImage,pixels]]
	
	# final pixel data must be flattened to 1D (and, if necessary, cropped)
	for fi,px in finalImages:
		# fast pixel updates using foreach_set:
		# https://projects.blender.org/blender/blender/commit/9075ec8269e7cb029f4fab6c1289eb2f1ae2858a
		pixel_buffer = px.reshape([virtImgHeight,virtImgWidth,4])[0:imgHeight,0:imgWidth].reshape(-1)
		fi.pixels.foreach_set(pixel_buffer)
		fi.update()
		
		if saveTo:
			fi.save()
	
	return newImage.name # pass back whatever the final name of the image ended up being

# https://learn.microsoft.com/en-us/windows/win32/api/dxgiformat/ne-dxgiformat-dxgi_format
# uses the "raw" values taken from the code rather than the ones in the MS enum (we aren't calling any MS code so we don't need it)
# only contains things we know of (rather than future-proofing with extra entries) since how're we supposed to guess what the raw numbers equate to
# (it's pretty obvious that 67 = BC2 and 76 = BC6, but those formats are rare anyway)
# [formatName, bitsPerPixel]
# possible additions: 1:R8Unorm, 41:R16G16B16A16Float, 109:B8G8R8A8Unorm, https://github.com/PredatorCZ/XenoLib/blob/master/include/xenolib/lbim.hpp
modernImageFormats = {
						37:["R8G8B8A8_UNORM",32],
						66:["BC1_UNORM",4], # aka DXT1
						68:["BC3_UNORM",8], # aka DXT5
						73:["BC4_UNORM",4],
						75:["BC5_UNORM",8],
						77:["BC7_UNORM",8],
					}

# BC7 needs a *lot* of external junk
# https://registry.khronos.org/DataFormat/specs/1.3/dataformat.1.3.html#bptc_bc7
# https://github.com/python-pillow/Pillow/blob/main/src/libImaging/BcnDecode.c
# [subsetCount, partitionBits, rotationBits, indexSelectionBits, colourBits, alphaBits, endpointPBits, sharedPBits, indexBits, index2Bits]
bc7ModeData = {
				0:[3, 4, 0, 0, 4, 0, 1, 0, 3, 0],
				1:[2, 6, 0, 0, 6, 0, 0, 1, 3, 0],
				2:[3, 6, 0, 0, 5, 0, 0, 0, 2, 0],
				3:[2, 6, 0, 0, 7, 0, 1, 0, 2, 0],
				4:[1, 0, 2, 1, 5, 6, 0, 0, 2, 3],
				5:[1, 0, 2, 0, 7, 8, 0, 0, 2, 2],
				6:[1, 0, 0, 0, 7, 7, 1, 0, 4, 0],
				7:[2, 6, 0, 0, 5, 5, 1, 0, 2, 0],
				}
bc7Weights = {
				2:[0, 21, 43, 64],
				3:[0, 9, 18, 27, 37, 46, 55, 64],
				4:[0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64],
				}
# bitmaps of which subsets each pixel uses, [row,column] order
bc7PartitionMaps = {
					2:[
						0xcccc, 0x8888, 0xeeee, 0xecc8, 0xc880, 0xfeec, 0xfec8, 0xec80,
						0xc800, 0xffec, 0xfe80, 0xe800, 0xffe8, 0xff00, 0xfff0, 0xf000,
						0xf710, 0x008e, 0x7100, 0x08ce, 0x008c, 0x7310, 0x3100, 0x8cce,
						0x088c, 0x3110, 0x6666, 0x366c, 0x17e8, 0x0ff0, 0x718e, 0x399c,
						0xaaaa, 0xf0f0, 0x5a5a, 0x33cc, 0x3c3c, 0x55aa, 0x9696, 0xa55a,
						0x73ce, 0x13c8, 0x324c, 0x3bdc, 0x6996, 0xc33c, 0x9966, 0x0660,
						0x0272, 0x04e4, 0x4e40, 0x2720, 0xc936, 0x936c, 0x39c6, 0x639c,
						0x9336, 0x9cc6, 0x817e, 0xe718, 0xccf0, 0x0fcc, 0x7744, 0xee22,
						],
					3:[
						0xaa685050, 0x6a5a5040, 0x5a5a4200, 0x5450a0a8, 0xa5a50000, 0xa0a05050, 0x5555a0a0, 0x5a5a5050,
						0xaa550000, 0xaa555500, 0xaaaa5500, 0x90909090, 0x94949494, 0xa4a4a4a4, 0xa9a59450, 0x2a0a4250,
						0xa5945040, 0x0a425054, 0xa5a5a500, 0x55a0a0a0, 0xa8a85454, 0x6a6a4040, 0xa4a45000, 0x1a1a0500,
						0x0050a4a4, 0xaaa59090, 0x14696914, 0x69691400, 0xa08585a0, 0xaa821414, 0x50a4a450, 0x6a5a0200,
						0xa9a58000, 0x5090a0a8, 0xa8a09050, 0x24242424, 0x00aa5500, 0x24924924, 0x24499224, 0x50a50a50,
						0x500aa550, 0xaaaa4444, 0x66660000, 0xa5a0a5a0, 0x50a050a0, 0x69286928, 0x44aaaa44, 0x66666600,
						0xaa444444, 0x54a854a8, 0x95809580, 0x96969600, 0xa85454a8, 0x80959580, 0xaa141414, 0x96960000,
						0xaaaa1414, 0xa05050a0, 0xa0a5a5a0, 0x96000000, 0x40804080, 0xa9a8a9a8, 0xaaaaaa44, 0x2a4a5254,
						],
					}
# one index per subset is stored wlith one fewer bit because it is known to be 0 - this is the list of such indexes
bc7AnchorIndexes = {
					"1/1":[0]*64,
					"1/2":[0]*64,
					"2/2":[
							15, 15, 15, 15, 15, 15, 15, 15,
							15, 15, 15, 15, 15, 15, 15, 15,
							15, 2, 8, 2, 2, 8, 8, 15,
							2, 8, 2, 2, 8, 8, 2, 2,
							15, 15, 6, 8, 2, 8, 15, 15,
							2, 8, 2, 2, 2, 15, 15, 6,
							6, 2, 6, 8, 15, 15, 2, 2,
							15, 15, 15, 15, 15, 2, 2, 15
							],
					"1/3":[0]*64,
					"2/3":[
							3, 3, 15, 15, 8, 3, 15, 15,
							8, 8, 6, 6, 6, 5, 3, 3,
							3, 3, 8, 15, 3, 3, 6, 10,
							5, 8, 8, 6, 8, 5, 15, 15,
							8, 15, 3, 5, 6, 10, 8, 15,
							15, 3, 15, 5, 15, 15, 15, 15,
							3, 15, 5, 5, 5, 8, 5, 10,
							5, 10, 8, 13, 15, 12, 3, 3
							],
					"3/3":[
							15, 8, 8, 3, 15, 15, 3, 8,
							15, 15, 15, 15, 15, 15, 15, 8,
							15, 8, 15, 3, 15, 8, 15, 8,
							3, 15, 6, 10, 15, 15, 10, 8,
							15, 3, 15, 10, 10, 8, 9, 10,
							6, 15, 8, 15, 3, 6, 6, 8,
							15, 3, 15, 15, 15, 15, 15, 15,
							15, 15, 15, 15, 3, 15, 15, 8
							],
					}

# much of this is just grabbed from XBC2MD, but only after understanding it (rather than blindly copy-pasting anything)
# REMINDER: don't manipulate image.pixels directly/individually or things will be dummy slow https://blender.stackexchange.com/questions/3673/
# references:
# 	https://www.vg-resource.com/thread-31389.html
# 	https://www.vg-resource.com/thread-33929.html
# 	https://en.wikipedia.org/wiki/Z-order_curve
# 	https://github.com/ScanMountGoat/tegra_swizzle
# 	https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression
# 	https://learn.microsoft.com/en-us/windows/win32/direct3d11/bc7-format
# 	https://github.com/python-pillow/Pillow/blob/main/src/libImaging/BcnDecode.c
# 	https://registry.khronos.org/DataFormat/specs/1.3/dataformat.1.3.html#bptc_bc7
def parse_texture_wismt(textureName,imgVersion,imgType,imgWidth,imgHeight,rawData,blueBC5,printProgress,overwrite=True,saveTo=None,dechannelise=False):
	try:
		imgFormat,bitsPerPixel = modernImageFormats[imgType]
	except KeyError:
		print_error(textureName+" is of an unknown/unsupported image type (id "+str(imgType)+")")
		return
	
	# first, check to see if image of the intended name exists already, and how to proceed
	try:
		existingImage = bpy.data.images[textureName]
		if overwrite:
			bpy.data.images.remove(existingImage)
	except KeyError as e: # no existing image of the same name
		pass # fine, move on
	newImage = bpy.data.images.new(textureName,imgWidth,imgHeight,alpha=True)
	# don't really want to do any of this until the end, but apparently setting the filepath after setting the pixels clears the image for no good reason
	newImage.file_format = "PNG"
	if saveTo:
		newImage.filepath = os.path.join(saveTo,textureName+".png")
	
	blockSize = 4 # in pixels
	unswizzleBufferSize = bitsPerPixel*2 # needs a better name at some point
	if imgFormat == "R8G8B8A8_UNORM": # blocks are single pixels rather than 4x4
		blockSize = 1
		unswizzleBufferSize = bitsPerPixel // 8
	# since the minimum block size is 4, images must be divisible by 4 - extend them as necessary
	virtImgWidth = imgWidth if imgWidth % blockSize == 0 else imgWidth + (blockSize - (imgWidth % blockSize))
	virtImgHeight = imgHeight if imgHeight % blockSize == 0 else imgHeight + (blockSize - (imgHeight % blockSize))
	# gotta create the image in full emptiness to start with, so we can random-access-fill the blocks as they come
	# Blender always needs alpha, so colours must be length 4
	pixels = numpy.zeros([virtImgHeight*virtImgWidth,4],dtype=numpy.float32)
	
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
	#print(imgFormat)
	
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
	bc7Mode8Flag = False
	for t in range(tileCount):
		if swizzlist[t] == -1:
			unassignedCount += 1
			continue
		if printProgress and t % 64 == 0: # printing for every single t racks up the import time a lot (e.g. 12s to 20s)
			print_progress_bar(t,tileCount,textureName)
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
			if imgFormat == "R8G8B8A8_UNORM":
				r = readAndParseInt(d,1)
				g = readAndParseInt(d,1)
				b = readAndParseInt(d,1)
				a = readAndParseInt(d,1)
				pixels[blockRootPixelX+blockRootPixelY*virtImgWidth] = [r/255.0,g/255.0,b/255.0,a/255.0]
			elif imgFormat == "BC1_UNORM" or imgFormat == "BC3_UNORM": # easy enough to treat these the same
				if imgFormat == "BC3_UNORM":
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
				# BC1_UNORM doesn't have "separate" alpha - no "else" needed
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
				if imgFormat == "BC3_UNORM" or endpoint0 > endpoint1:
					colours[2] = [2/3*colours[0][0]+1/3*colours[1][0],2/3*colours[0][1]+1/3*colours[1][1],2/3*colours[0][2]+1/3*colours[1][2],1.0]
					colours[3] = [1/3*colours[0][0]+2/3*colours[1][0],1/3*colours[0][1]+2/3*colours[1][1],1/3*colours[0][2]+2/3*colours[1][2],1.0]
				else: # BC1_UNORM and endpoint0 < endpoint1
					colours[2] = [1/2*colours[0][0]+1/2*colours[1][0],1/2*colours[0][1]+1/2*colours[1][1],1/2*colours[0][2]+1/2*colours[1][2],1.0]
					colours[3] = [0.0,0.0,0.0,0.0] # binary alpha
				pixelIndexes = [
								(row3 & 0b00000011), (row3 & 0b00001100) >> 2, (row3 & 0b00110000) >> 4, (row3 & 0b11000000) >> 6,
								(row2 & 0b00000011), (row2 & 0b00001100) >> 2, (row2 & 0b00110000) >> 4, (row2 & 0b11000000) >> 6,
								(row1 & 0b00000011), (row1 & 0b00001100) >> 2, (row1 & 0b00110000) >> 4, (row1 & 0b11000000) >> 6,
								(row0 & 0b00000011), (row0 & 0b00001100) >> 2, (row0 & 0b00110000) >> 4, (row0 & 0b11000000) >> 6,
								]
				if imgFormat == "BC3_UNORM":
					for p,pi in enumerate(pixelIndexes):
						pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = colours[pi][0:3]+[alphas[alphaIndexes[p]]/255.0]
				else: # BC1_UNORM
					for p,pi in enumerate(pixelIndexes):
						pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = colours[pi]
			elif imgFormat == "BC4_UNORM" or imgFormat == "BC5_UNORM": # BC5 is just two BC4s stapled together
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
				if imgFormat == "BC4_UNORM":
					pixelIndexes = [redIndexes[i] for i in [12,13,14,15,8,9,10,11,4,5,6,7,0,1,2,3]]
					for p,pi in enumerate(pixelIndexes):
						value = reds[pi]/255.0
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
			elif imgFormat == "BC7_UNORM":
				block = d.read(16)
				bits = BitReader(block,reverse=True)
				mode = 0
				for i in range(8):
					modeBit = bits.readbits(1)
					if modeBit:
						break
					mode += 1
				if mode >= 8: # reserved, ought to never happen but returning [0,0,0,0] is da rulez
					bc7Mode8Flag = True
					for p in range(16):
						pixels[(blockRootPixelX + p % 4) + ((blockRootPixelY + p // 4) * virtImgWidth)] = [0,0,0,0]
					continue
				subsetCount,partitionBits,rotationBits,indexSelectionBits,colourBits,alphaBits,endpointPBits,sharedPBits,indexBits,index2Bits = bc7ModeData[mode]
				partitionPattern = 0
				if partitionBits > 0:
					partitionPattern = bits.readbits(partitionBits)
				rotationPattern = 0
				if rotationBits > 0:
					rotationPattern = bits.readbits(rotationBits)
				indexSelectionPattern = 0
				if indexSelectionBits > 0:
					indexSelectionPattern = bits.readbits(indexSelectionBits)
				partitionMap = [0]*16
				if subsetCount == 2:
					bitstring = format(bc7PartitionMaps[2][partitionPattern],"016b")
					partitionMap = [int(x,2) for x in bitstring]
				elif subsetCount == 3:
					bitstring = format(bc7PartitionMaps[3][partitionPattern],"032b")
					partitionMap = [int(bitstring[x*2:x*2+2],2) for x in range(16)]
				# must be reversed because it's just safer to leave the copy-pasted map data as-is than to reverse it all manually
				partitionMap.reverse()
				endpointsR = []
				endpointsG = []
				endpointsB = []
				endpointsA = []
				endpointsP = []
				subsetsP = []
				colourIndexes = []
				alphaIndexes = []
				indexSizes = [indexBits,indexBits] # colour, alpha
				# this copy-paste of all the fors is annoying but necessary because things must be read in order
				subIter = range(subsetCount)
				for s in subIter:
					endpointsR.append([bits.readbits(colourBits),bits.readbits(colourBits)])
				for s in subIter:
					endpointsG.append([bits.readbits(colourBits),bits.readbits(colourBits)])
				for s in subIter:
					endpointsB.append([bits.readbits(colourBits),bits.readbits(colourBits)])
				for s in subIter:
					endpointsA.append([bits.readbits(alphaBits),bits.readbits(alphaBits)])
				for s in subIter:
					endpointsP.append([bits.readbits(endpointPBits),bits.readbits(endpointPBits)])
				for s in subIter:
					subsetsP.append(bits.readbits(sharedPBits))
				for p in range(16):
					subset = partitionMap[p]
					anchorIndex = bc7AnchorIndexes[str(subset+1)+"/"+str(subsetCount)][partitionPattern]
					indexSizeMod = 0
					if p == anchorIndex:
						indexSizeMod = -1
					if indexSelectionPattern:
						alphaIndexes.append(bits.readbits(indexBits+indexSizeMod))
					else:
						colourIndexes.append(bits.readbits(indexBits+indexSizeMod))
				if index2Bits > 0:
					for p in range(16):
						subset = partitionMap[p]
						anchorIndex = bc7AnchorIndexes[str(subset+1)+"/"+str(subsetCount)][partitionPattern]
						indexSizeMod = 0
						if p == anchorIndex:
							indexSizeMod = -1
						if indexSelectionPattern: # reminder: this is the reverse of the first
							colourIndexes.append(bits.readbits(index2Bits+indexSizeMod))
							indexSizes[0] = index2Bits
						else:
							alphaIndexes.append(bits.readbits(index2Bits+indexSizeMod))
							indexSizes[1] = index2Bits
				# reading done, now for endpoint interpolation
				reds = []
				greens = []
				blues = []
				alphas = []
				for s in subIter:
					ra = []
					ga = []
					ba = []
					aa = []
					for ep in [0,1]:
						r = endpointsR[s][ep]
						g = endpointsG[s][ep]
						b = endpointsB[s][ep]
						a = endpointsA[s][ep]
						if endpointPBits > 0:
							r = (r << 1) | endpointsP[s][ep]
							g = (g << 1) | endpointsP[s][ep]
							b = (b << 1) | endpointsP[s][ep]
							if alphaBits > 0:
								a = (a << 1) | endpointsP[s][ep]
						if sharedPBits > 0:
							r = (r << 1) | subsetsP[s]
							g = (g << 1) | subsetsP[s]
							b = (b << 1) | subsetsP[s]
							if alphaBits > 0:
								a = (a << 1) | subsetsP[s]
						cb = colourBits+endpointPBits+sharedPBits
						ab = alphaBits+endpointPBits+sharedPBits if alphaBits > 0 else 0
						r = (r << (8 - cb)) | ((r << (8 - cb)) >> cb)
						g = (g << (8 - cb)) | ((g << (8 - cb)) >> cb)
						b = (b << (8 - cb)) | ((b << (8 - cb)) >> cb)
						if alphaBits > 0:
							a = (a << (8 - ab)) | ((a << (8 - ab)) >> ab)
						ra.append(r)
						ga.append(g)
						ba.append(b)
						if alphaBits > 0:
							aa.append(a)
						else:
							aa.append(255)
					cw = bc7Weights[indexSizes[0]]
					aw = bc7Weights[indexSizes[1]]
					reds.append([((64-w)*ra[0]+w*ra[1]+32) >> 6 for w in cw])
					greens.append([((64-w)*ga[0]+w*ga[1]+32) >> 6 for w in cw])
					blues.append([((64-w)*ba[0]+w*ba[1]+32) >> 6 for w in cw])
					alphas.append([((64-w)*aa[0]+w*aa[1]+32) >> 6 for w in aw])
				# and now finally actually setting the pixels
				for p in range(16):
					subset = partitionMap[p]
					r = reds[subset][colourIndexes[p]]
					g = greens[subset][colourIndexes[p]]
					b = blues[subset][colourIndexes[p]]
					if alphaIndexes:
						a = alphas[subset][alphaIndexes[p]]
					else:
						a = 255
					if rotationPattern == 1:
						r,a = a,r
					elif rotationPattern == 2:
						g,a = a,g
					elif rotationPattern == 3:
						b,a = a,b
					pi = [12,13,14,15,8,9,10,11,4,5,6,7,0,1,2,3][p]
					pixels[(blockRootPixelX + pi % 4) + ((blockRootPixelY + pi // 4) * virtImgWidth)] = [r/255.0,g/255.0,b/255.0,a/255.0]
	if printProgress:
		print_progress_bar(tileCount,tileCount,textureName)
	if unassignedCount > 0:
		print_error("Texture "+textureName+" didn't complete deswizzling correctly: "+str(unassignedCount)+" / "+str(tileCountY*tileCountX)+" tiles unassigned")
	if bc7Mode8Flag:
		print_warning("Texture "+textureName+" contained illegal BC7 blocks (rendered as transparent black)")
	d.close()
	
	finalImages = [[newImage,pixels]]

	if dechannelise:
		for i,c in enumerate(["r","g","b","a"]):
			splitName = textureName+"_"+c
			try:
				existingSplitImage = bpy.data.images[splitName]
				if overwrite:
					bpy.data.images.remove(existingSplitImage)
			except KeyError as e: # no existing image of the same name
				pass # fine, move on
			newSplitImage = bpy.data.images.new(splitName,imgWidth,imgHeight)
			# don't really want to do any of this until the end, but apparently setting the filepath after setting the pixels clears the image for no good reason
			newSplitImage.file_format = "PNG"
			if saveTo:
				newSplitImage.filepath = os.path.join(saveTo,splitName+".png")
			# detect channels that are entirely black or white and don't include them
			# if a channel is entirely some sort of grey, that's still worth including
			# todo: make this a config option
			mono = True
			first = pixels[0][i]
			if first != 0 and first != 1:
				mono = False
			# this check is quick enough even on big images it can be done separately
			for j,p in enumerate(pixels):
				if p[i] != first:
					mono = False
					break
			if mono:
				if printProgress:
					print("Excluding channel "+c.upper()+" (all pixels "+str(first)+")")
				bpy.data.images.remove(newSplitImage)
				continue
			
			# assign the selected single channel to the RGB channels
			splitPixels = numpy.zeros([virtImgHeight*virtImgWidth,4],dtype=numpy.float32)
			splitPixels[:,0] = pixels[:,i]
			splitPixels[:,1] = pixels[:,i]
			splitPixels[:,2] = pixels[:,i]
			splitPixels[:,3] = 1.0
			
			finalImages.append([newSplitImage,splitPixels])
	
	# final pixel data must be flattened to 1D (and, if necessary, cropped)
	for fi,px in finalImages:
		# fast pixel updates using foreach_set:
		# https://projects.blender.org/blender/blender/commit/9075ec8269e7cb029f4fab6c1289eb2f1ae2858a
		pixel_buffer = px.reshape([virtImgHeight,virtImgWidth,4])[0:imgHeight,0:imgWidth].reshape(-1)
		fi.pixels.foreach_set(pixel_buffer)
		fi.update()
		
		if saveTo:
			fi.save()
	
	return newImage.name # pass back whatever the final name of the image ended up being

def register():
	pass

def unregister():
	pass

#[...]