# because just packing/unpacking arrays gets old and error-prone

def ensure_type(var,type):
	if not isinstance(var,type):
		raise TypeError("expected "+str(type)+", not "+str(type(x)))
def ensure_length(seq,length):
	if len(seq) != length:
		raise ValueError("sequence must be length "+str(length)+", not "+str(len(seq)))

class MonadoForgeBone:
	def __init__(self,i):
		self._name = "Bone"
		self._index = i
		self._parent = -1
		self._position = [0,0,0,1] # x, y, z, w
		self._rotation = [1,0,0,0] # w, x, y, z
		self._scale = [1,1,1,1] # x, y, z, w
		self._endpoint = False
	
	# no setter (index should be immutable)
	def getIndex(self):
		return self._index
	
	def getName(self):
		return self._name
	def setName(self,name):
		ensure_type(name,str)
		self._name = name
	
	def getParent(self):
		return self._parent
	def clearParent(self):
		self._parent = -1
	def setParent(self,parent):
		ensure_type(parent,int)
		self._parent = parent
	
	def getPosition(self):
		return self._position
	def setPosition(self,pos):
		ensure_length(pos,4)
		self._position = pos[:]
	
	def getRotation(self):
		return self._rotation
	def setRotation(self,rot):
		ensure_length(rot,4)
		self._rotation = rot[:]
	
	def getScale(self):
		return self._scale
	def setScale(self,scl):
		ensure_length(scl,4)
		self._scale = scl[:]
	
	def isEndpoint(self):
		return self._endpoint
	def setEndpoint(self,ep):
		ensure_type(ep,bool)
		self._endpoint = ep

class MonadoForgeSkeleton:
	def __init__(self):
		self._bones = []
	
	def getBones(self):
		return self._bones
	def clearBones(self):
		self._bones = []
	def addBone(self,bone):
		ensure_type(bone,MonadoForgeBone)
		self._bones.append(bone)
	def setBones(self,bones):
		self.clearBones()
		for b in bones:
			self.addBone(b)

# this class is specifically for keeping hold of wimdo data to be passed to a wismt
class MonadoForgeWimdoMaterial:
	def __init__(self,i):
		self._index = i
		self._name = "Material"
		self._baseColour = [1.0,1.0,1.0,1.0]
		self._textureTable = [] # [[texture id,sampler id,???,???]]
		self._samplers = [] # [[flags,float]]
		self._extraData = []
		self._extraDataIndex = 0 # needed because of how extra data needs to be read separately
		self._renderPassType = 0
	
	def getIndex(self):
		return self._index
	# no setter (index should be immutable)
	
	def getName(self):
		return self._name
	def setName(self,name):
		ensure_type(name,str)
		self._name = name
	
	def getBaseColour(self):
		return self._baseColour
	def setBaseColour(self,col):
		ensure_length(col,4)
		self._baseColour = col[:]
	
	def getTextureTable(self):
		return self._textureTable
	def clearTextureTable(self):
		self._textureTable = []
	def addTextureTableItem(self,tti):
		ensure_length(tti,4)
		self._textureTable.append(tti)
	def setTextureTable(self,table):
		ensure_type(table,list)
		for tt in table:
			self.addTextureTableItem(tt)
	
	def getSamplers(self):
		return self._samplers
	def clearSamplers(self):
		self._samplers = []
	def addSampler(self,sampler):
		ensure_length(sampler,2)
		self._samplers.append(sampler)
	def setSamplers(self,samplers):
		ensure_type(samplers,list)
		for s in samplers:
			self.addSampler(s)
	
	def getExtraData(self):
		return self._extraData
	def clearExtraData(self):
		self._extraData = []
	def addExtraData(self,ex):
		ensure_type(ex,float)
		self._extraData.append(ex)
	def setExtraData(self,exs):
		self.clearExtraData()
		for ex in exs:
			self.addExtraData(ex)
	
	def getExtraDataIndex(self):
		return self._extraDataIndex
	def setExtraDataIndex(self,xdi):
		ensure_type(xdi,int)
		self._extraDataIndex = xdi
	
	def getRenderPassType(self):
		return self._renderPassType
	def setRenderPassType(self,rpt):
		ensure_type(rpt,int)
		self._renderPassType = rpt

class MonadoForgeTexture: # 2D only, no 3D texture support (for now?)
	def __init__(self):
		self._name = "Texture"
		self._repeating = [False,False] # False = clamp, True = repeat (default False because "weird solid colour" is easier to see as a potential mistake than "minor cross-edge bleeding")
		self._mirroring = [False,False]
		self._isFiltered = True # False = nearest, True = linear
	
	def getName(self):
		return self._name
	def setName(self,name):
		ensure_type(name,str)
		self._name = name
	
	def getRepeating(self):
		return self._repeating
	def setRepeating(self,rpt):
		ensure_length(rpt,2)
		self._repeating = rpt[:]
	
	def getMirroring(self):
		return self._mirroring
	def setMirroring(self,mir):
		ensure_length(mir,2)
		self._mirroring = mir[:]
	
	def isFiltered(self):
		return self._isFiltered
	def setFiltered(self,filt):
		ensure_type(filt,bool)
		self._isFiltered = filt

class MonadoForgeMaterial:
	def __init__(self,i):
		self._index = i
		self._name = "Material"
		self._baseColour = [1.0,1.0,1.0,1.0]
		self._viewportColour = [0.5,0.5,0.5,1.0]
		self._culling = [False,True] # front, back
		self._transparency = 0 # 0 = opaque, 1 = alpha clip, 2 = alpha blend
		self._textures = []
		self._extraData = []
		self._colourLayerCount = 0 # not actually part of the material, but the material needs to know
		self._uvLayerCount = 0 # same
	
	# no setter (index should be immutable)
	def getIndex(self):
		return self._index
	
	def getName(self):
		return self._name
	def setName(self,name):
		ensure_type(name,str)
		self._name = name
	
	def getBaseColour(self):
		return self._baseColour
	def setBaseColour(self,col):
		ensure_length(col,4)
		self._baseColour = col[:]
	
	def getViewportColour(self):
		return self._viewportColour
	def setViewportColour(self,vpc):
		ensure_length(vpc,4)
		self._viewportColour = vpc[:]
	
	def getCulling(self):
		return self._culling
	def getCullingFront(self):
		return self._culling[0]
	def getCullingBack(self):
		return self._culling[1]
	def setCulling(self,cull):
		ensure_length(cull,2)
		self._culling = cull[:]
	def setCullingFront(self,cull):
		ensure_type(cull,bool)
		self._culling[0] = cull
	def setCullingBack(self,cull):
		ensure_type(cull,bool)
		self._culling[1] = cull
	
	def getTransparency(self):
		return self._transparency
	def setTransparency(self,trns):
		ensure_type(trns,int)
		self._transparency = trns
	def isOpaque(self):
		return self._transparency == 0
	def isTransparent(self):
		return self._transparency > 0
	def isAlphaClip(self):
		return self._transparency == 1
	def isAlphaBlend(self):
		return self._transparency == 2

	def getTextures(self):
		return self._textures
	def clearTextures(self):
		self._textures = []
	def addTexture(self,tex):
		ensure_type(tex,MonadoForgeTexture)
		self._textures.append(tex)
	def setTextures(self,texs):
		self.clearTextures()
		for tex in texs:
			self.addTexture(texs)
	
	def getExtraData(self):
		return self._extraData
	def clearExtraData(self):
		self._extraData = []
	def addExtraData(self,ex):
		ensure_type(ex,float)
		self._extraData.append(ex)
	def setExtraData(self,exs):
		self.clearExtraData()
		for ex in exs:
			self.addExtraData(ex)
	
	def getColourLayerCount(self):
		return self._colourLayerCount
	def setColourLayerCount(self,clc):
		ensure_type(clc,int)
		self._colourLayerCount = clc
	
	def getUVLayerCount(self):
		return self._uvLayerCount
	def setUVLayerCount(self,uvlc):
		ensure_type(uvlc,int)
		self._uvLayerCount = uvlc

class MonadoForgeVertex:
	def __init__(self,i):
		self._index = i
		self._position = [0,0,0] # having position ever be None seems to cause Problems
		self._loops = {} # keyed by face index
		self._weightSetIndex = -1 # pre-bake
		self._weights = {} # post-bake (must also be by index rather than name since we don't necessarily know names)
		self._normal = None
		self._uvs = {}
		self._colours = {} # in 255 format
	
	def getIndex(self):
		return self._index
	# no setter, immutable
	
	def getPosition(self):
		return self._position
	def setPosition(self,pos):
		ensure_length(pos,3)
		self._position = pos[:]
	# there is no "clearPosition" because of the None problem
	
	def getLoops(self):
		return self._loops
	def getLoop(self,faceIndex):
		ensure_type(faceIndex,int)
		return self._loops[faceIndex]
	def clearLoops(self):
		self._loops = {}
	def createLoop(self,faceIndex):
		ensure_type(faceIndex,int)
		if faceIndex in self._loops.keys(): # (currently) do not want this to be a valid operation, too much potential for silent problems
			raise ValueError("vertex "+str(self._index)+" already has a loop with face "+str(faceIndex))
		self._loops[faceIndex] = MonadoForgeLoop(self._index,faceIndex)
	def addLoop(self,loop):
		ensure_type(loop,MonadoForgeLoop)
		faceIndex = loop.getFace()
		if faceIndex in self._loops.keys(): # (currently) do not want this to be a valid operation, too much potential for silent problems
			raise ValueError("vertex "+str(self._index)+" already has a loop with face "+str(faceIndex))
		self._loops[faceIndex] = loop
	# there is no bulk "setLoops", for now anyway
	
	def hasUVs(self):
		return self._uvs != {}
	def getUVs(self):
		return self._uvs
	def getUV(self,layer):
		return self._uvs[layer]
	def clearUVs(self):
		self._uvs = {}
	def setUV(self,layer,uv):
		ensure_length(uv,2)
		self._uvs[layer] = uv
	
	def hasNormal(self):
		return self._normal != None
	def getNormal(self):
		return self._normal
	def clearNormal(self):
		self._normal = None
	def setNormal(self,nrm):
		ensure_length(nrm,3)
		self._normal = nrm[:]
	
	def hasColours(self):
		return self._colours != {}
	def getColours(self):
		return self._colours
	def getColour(self,layer):
		return self._colours[layer]
	def clearColours(self):
		self._colours = []
	def setColour(self,layer,colour):
		ensure_length(colour,4) # Blender really pushes alpha for everything
		self._colours[layer] = colour[:]
	
	def hasWeightIndex(self):
		return self._weightSetIndex != -1
	def getWeightSetIndex(self):
		return self._weightSetIndex
	def clearWeightSetIndex(self):
		self._weightSetIndex = -1
	def setWeightSetIndex(self,wsi):
		ensure_type(wsi,int)
		self._weightSetIndex = wsi
	
	def hasWeights(self):
		return self._weights != {}
	def getWeights(self):
		return self._weights
	def getWeight(self,groupIndex):
		return self._weights[groupIndex]
	def clearWeights(self):
		self._weights = {}
	def setWeight(self,groupIndex,weight):
		ensure_type(weight,float)
		self._weights[groupIndex] = weight
	
	def isDouble(self,other):
		return self == other or (
			self._position == other._position and
			self._uvs == other._uvs and
			self._normal == other._normal and
			self._colours == other._colours and
			self._weightSetIndex == other._weightSetIndex and
			self._weights == other._weights
		)

class MonadoForgeFace:
	def __init__(self,i):
		self._index = i
		self._vertexIndexes = []
		self._materialIndex = 0
	
	def getIndex(self):
		return self._index
	# no setter, immutable
	
	def getVertexIndexes(self):
		return self._vertexIndexes
	def clearVertexIndexes(self):
		self._vertexIndexes = []
	def addVertexIndex(self,v):
		ensure_type(v,int)
		self._vertexIndexes.append(v)
	def setVertexIndexes(self,v):
		self._vertexIndexes = v[:]

# the fact that the official API has to explain that "loop" means "face corner" tells us how bad even they think the term is
# but it's probably better to just use it than to make something else up just for this add-on
class MonadoForgeLoop:
	def __init__(self,v,f):
		self._vertex = v
		self._face = f
		self._normal = None
		self._uvs = {}
		self._colours = {} # in 255 format
	
	def getVertex(self):
		return self._vertex
	def getFace(self):
		return self._face
	# not settable; intended to be immutable
	
	def hasNormal(self):
		return self._normal != None
	def getNormal(self):
		return self._normal
	def clearNormal(self):
		self._normal = None
	def setNormal(self,nrm):
		ensure_length(nrm,3)
		self._normal = nrm[:]
	
	def hasUVs(self):
		return self._uvs != {}
	def getUVs(self):
		return self._uvs
	def getUV(self,layer):
		return self._uvs[layer]
	def clearUVs(self):
		self._uvs = {}
	def setUV(self,layer,uv):
		ensure_length(uv,2)
		self._uvs[layer] = uv
	
	def hasColours(self):
		return self._colours != {}
	def getColours(self):
		return self._colours
	def getColour(self,layer):
		return self._colours[layer]
	def clearColours(self):
		self._colours = []
	def setColour(self,layer,colour):
		ensure_length(colour,4) # Blender really pushes alpha for everything
		self._colours[layer] = colour[:]

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
	def setName(self,name):
		ensure_type(name,str)
		self._name = name

class MonadoForgeMesh:
	def __init__(self):
		self._name = ""
		self._vertices = []
		self._faces = []
		self._weightSets = [] # because it can be convenient to hold these here and have vertexes just refer with index
		self._shapes = [] # list of MonadoForgeMeshShapes
		self._materialIndex = -1
	
	def getName(self):
		return self._name
	def setName(self,name):
		ensure_type(name,str)
		self._name = name
	
	def getVertices(self):
		return self._vertices
	def clearVertices(self):
		self._vertices = []
	def addVertex(self,v):
		ensure_type(v,MonadoForgeVertex)
		self._vertices.append(v)
	def setVertices(self,verts):
		self.clearVertices()
		for v in verts:
			self.addVertex(v)
	
	def getFaces(self):
		return self._faces
	def clearFaces(self):
		self._faces = []
	def addFace(self,f):
		ensure_type(f,MonadoForgeFace)
		self._faces.append(f)
	def setFaces(self,faces):
		self.clearFaces()
		for f in faces:
			self.addFace(f)
	
	def getWeightSets(self):
		return self._weightSets
	def clearWeightSets(self):
		self._weightSets = []
	def addWeightSet(self,ws):
		ensure_type(ws,list)
		self._weightSets.append(ws)
	def setWeightSets(self,ws):
		ensure_type(ws,list)
		self._weightSets = ws
	
	def getShapes(self):
		return self._shapes
	def clearShapes(self):
		self._shapes = []
	def addShape(self,shape):
		ensure_type(shape,MonadoForgeMeshShape)
		self._shapes.append(shape)
	def setShapes(self,shapeList):
		self.clearShapes()
		for s in shapeList:
			self.addShape(s)
	
	def getMaterialIndex(self):
		return self._materialIndex
	def setMaterialIndex(self,i):
		ensure_type(i,int)
		self._materialIndex = i
	
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
			if v.hasColours(): return True
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
	def getColourLayerList(self):
		layers = []
		for v in self._vertices:
			layers += [k for k in v.getColours().keys()]
		return list(set(layers))
	def getVertexColoursLayer(self,layer):
		return [v.getColours()[layer] for v in self._vertices]
	def getVertexWeightIndexesList(self):
		return [v.getWeightSetIndex() for v in self._vertices]
	def getVertexWeightsList(self):
		return [v.getWeights() for v in self._vertices]
	def getVertexesInWeightGroup(self,groupID):
		return [v for v in self._vertices if groupID in v.getWeights().keys()]
	def getVertexesWithWeightIndex(self,index):
		return [v for v in self._vertices if v.getWeightSetIndex() == index]
	def getFaceVertexIndexesList(self):
		return [f.getVertexIndexes() for f in self._faces]

class MonadoForgeMeshHeader:
	# intended to be immutable, so all the setting is in the constructor
	def __init__(self,id,mf1,mf2,vt,ft,mm,lod):
		self._meshID = id
		self._meshFlags1 = mf1
		self._meshFlags2 = mf2
		self._meshVertTableIndex = vt
		self._meshFaceTableIndex = ft
		self._meshMaterialIndex = mm
		self._meshLODValue = lod
	def getMeshID(self):
		return self._meshID
	def getMeshFlags1(self):
		return self._meshFlags1
	def getMeshFlags2(self):
		return self._meshFlags2
	def getMeshVertTableIndex(self):
		return self._meshVertTableIndex
	def getMeshFaceTableIndex(self):
		return self._meshFaceTableIndex
	def getMeshMaterialIndex(self):
		return self._meshMaterialIndex
	def getMeshLODValue(self):
		return self._meshLODValue

# this class is specifically for passing wimdo results to wismt import
# assumption: there can only be one skeleton from the .wimdo and a second from an external source (i.e. an .arc/.chr file)
class MonadoForgeWimdoPackage:
	def __init__(self,skel,skelEx,mh,sh,mat):
		ensure_type(skel,MonadoForgeSkeleton)
		if skelEx:
			ensure_type(skelEx,MonadoForgeSkeleton)
		ensure_type(mh,list)
		ensure_type(sh,list)
		ensure_type(mat,list)
		self._skeleton = skel
		self._externalSkeleton = skelEx
		self._meshHeaders = mh
		self._shapeHeaders = sh
		self._materials = mat
	def getSkeleton(self):
		return self._skeleton
	def getExternalSkeleton(self):
		return self._externalSkeleton
	def getMeshHeaders(self):
		return self._meshHeaders
	def getShapeHeaders(self):
		return self._shapeHeaders
	def getMaterials(self):
		return self._materials
	
	def getLODList(self):
		lods = []
		for mh in self._meshHeaders:
			lods.append(mh.getMeshLODValue())
		return list(set(lods))
	def getBestLOD(self):
		return min(self.getLODList())

# this is intended to be used only once everything game-specific is done and the data is fully in agnostic format
# same skeleton assumptions as the wimdo package
class MonadoForgeImportedPackage:
	def __init__(self):
		self._skeleton = None
		self._externalSkeleton = None
		self._meshes = []
		self._materials = []
	
	def getSkeleton(self):
		return self._skeleton
	def setSkeleton(self,skeleton):
		self._skeleton = skeleton
	
	def getExternalSkeleton(self):
		return self._externalSkeleton
	def setExternalSkeleton(self,externalSkeleton):
		self._externalSkeleton = externalSkeleton
	
	def getMeshes(self):
		return self._meshes
	def clearMeshes(self):
		self._meshes = []
	def addMesh(self,mesh):
		self._meshes.append(mesh)
	def setMeshes(self,meshes):
		self._meshes = meshes[:]
	
	def getMaterials(self):
		return self._materials
	def clearMaterials(self):
		self._materials = []
	def addMaterial(self,material):
		self._materials.append(material)
	def setMaterials(self,material):
		self._materials = material[:]

def register():
	pass

def unregister():
	pass

#[...]