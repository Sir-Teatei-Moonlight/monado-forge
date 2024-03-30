# because just packing/unpacking arrays gets old and error-prone

def ensure_type(var,intended):
	if not isinstance(var,intended):
		raise TypeError("expected "+str(intended)+", not "+str(type(var)))
def ensure_length(seq,length):
	if len(seq) != length:
		raise ValueError("sequence must be length "+str(length)+", not "+str(len(seq)))
def ensure_range(var,min,max):
	if var < min or var > max:
		raise ValueError("value "+str(var)+" is outside range "+str(min)+" - "+str(max))

class MonadoForgeBone:
	def __init__(self,i):
		self._index = i
		self._name = "Bone"
		self._parent = -1
		self._position = [0,0,0,1] # x, y, z, w
		self._rotation = [1,0,0,0] # w, x, y, z
		self._scale = [1,1,1,1] # x, y, z, w
		self._isEndpoint = False
	
	@property
	def index(self):
		return self._index
	# no setter
	
	@property
	def name(self):
		return self._name
	@name.setter
	def name(self,value):
		ensure_type(value,str)
		self._name = value
	
	@property
	def parent(self):
		return self._parent
	@parent.setter
	def parent(self,value):
		ensure_type(value,int)
		self._parent = value
	
	@property
	def position(self):
		return self._position
	@position.setter
	def position(self,value):
		ensure_length(value,4)
		self._position = value[:]
	
	@property
	def rotation(self):
		return self._rotation
	@rotation.setter
	def rotation(self,value):
		ensure_length(value,4)
		self._rotation = value[:]
	
	@property
	def scale(self):
		return self._scale
	@scale.setter
	def scale(self,value):
		ensure_length(value,4)
		self._scale = value[:]
	
	@property
	def isEndpoint(self):
		return self._isEndpoint
	@isEndpoint.setter
	def isEndpoint(self,value):
		ensure_type(value,bool)
		self._isEndpoint = value

class MonadoForgeSkeleton:
	def __init__(self):
		self._bones = []
	
	@property
	def bones(self):
		return self._bones
	@bones.setter
	def bones(self,value):
		self.clearBones()
		for b in value:
			self.addBone(b)
	def clearBones(self):
		self._bones = []
	def addBone(self,bone):
		ensure_type(bone,MonadoForgeBone)
		self._bones.append(bone)

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
	
	@property
	def index(self):
		return self._index
	# no setter
	
	@property
	def name(self):
		return self._name
	@name.setter
	def name(self,value):
		ensure_type(value,str)
		self._name = value
	
	@property
	def baseColour(self):
		return self._baseColour
	@baseColour.setter
	def baseColour(self,value):
		ensure_length(value,4)
		self._baseColour = value[:]
	
	@property
	def textureTable(self):
		return self._textureTable
	@textureTable.setter
	def textureTable(self,value):
		self.clearTextureTable()
		for tt in value:
			self.addTextureTableItem(tt)
	def clearTextureTable(self):
		self._textureTable = []
	def addTextureTableItem(self,tti):
		ensure_length(tti,4)
		self._textureTable.append(tti)
	
	@property
	def samplers(self):
		return self._samplers
	@samplers.setter
	def samplers(self,value):
		self.clearSamplers()
		for s in value:
			self.addSampler(s)
	def clearSamplers(self):
		self._samplers = []
	def addSampler(self,sampler):
		ensure_length(sampler,2)
		self._samplers.append(sampler)
	
	@property
	def extraData(self):
		return self._extraData
	@extraData.setter
	def extraData(self,value):
		self.clearExtraData()
		for ex in value:
			self.addExtraData(ex)
	def clearExtraData(self):
		self._extraData = []
	def addExtraData(self,ex):
		ensure_type(ex,float)
		self._extraData.append(ex)
	
	@property
	def extraDataIndex(self):
		return self._extraDataIndex
	@extraDataIndex.setter
	def extraDataIndex(self,value):
		ensure_type(value,int)
		self._extraDataIndex = value
	
	@property
	def renderPassType(self):
		return self._renderPassType
	@renderPassType.setter
	def renderPassType(self,value):
		ensure_type(value,int)
		self._renderPassType = value

class MonadoForgeTexture: # 2D only, no 3D texture support (for now?)
	def __init__(self):
		self._name = "Texture"
		self._repeating = [False,False] # False = clamp, True = repeat (default False because "weird solid colour" is easier to see as a potential mistake than "minor cross-edge bleeding")
		self._mirroring = [False,False]
		self._isFiltered = True # False = nearest, True = linear
	
	@property
	def name(self):
		return self._name
	@name.setter
	def name(self,value):
		ensure_type(value,str)
		self._name = value
	
	@property
	def repeating(self):
		return self._repeating
	@repeating.setter
	def repeating(self,value):
		ensure_length(value,2)
		self._repeating = value[:]
	
	@property
	def mirroring(self):
		return self._mirroring
	@mirroring.setter
	def mirroring(self,value):
		ensure_length(value,2)
		self._mirroring = value[:]
	
	@property
	def isFiltered(self):
		return self._isFiltered
	@isFiltered.setter
	def isFiltered(self,value):
		ensure_type(value,bool)
		self._isFiltered = value

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
	
	@property
	def index(self):
		return self._index
	# no setter
	
	@property
	def name(self):
		return self._name
	@name.setter
	def name(self,value):
		ensure_type(value,str)
		self._name = value
	
	@property
	def baseColour(self):
		return self._baseColour
	@baseColour.setter
	def baseColour(self,value):
		ensure_length(value,4)
		self._baseColour = value[:]
	
	@property
	def viewportColour(self):
		return self._viewportColour
	@viewportColour.setter
	def viewportColour(self,value):
		ensure_length(value,4)
		self._viewportColour = value[:]
	
	@property
	def culling(self):
		return self._culling
	@culling.setter
	def culling(self,value):
		ensure_length(value,2)
		self._culling = value[:]
	@property
	def cullingFront(self):
		return self._culling[0]
	@cullingFront.setter
	def cullingFront(self,value):
		ensure_type(value,bool)
		self._culling[0] = value
	@property
	def cullingBack(self):
		return self._culling[1]
	@cullingBack.setter
	def cullingBack(self,value):
		ensure_type(value,bool)
		self._culling[1] = value
	
	@property
	def transparency(self):
		return self._transparency
	@transparency.setter
	def transparency(self,value):
		ensure_type(value,int)
		ensure_range(value,0,2)
		self._transparency = value
	@property
	def isOpaque(self):
		return self._transparency == 0
	# no setter
	@property
	def isTransparent(self):
		return self._transparency > 0
	# no setter
	@property
	def isAlphaClip(self):
		return self._transparency == 1
	# no setter
	@property
	def isAlphaBlend(self):
		return self._transparency == 2
	# no setter
	
	@property
	def textures(self):
		return self._textures
	@textures.setter
	def textures(self,value):
		self.clearTextures()
		for tex in value:
			self.addTexture(texs)
	def clearTextures(self):
		self._textures = []
	def addTexture(self,tex):
		ensure_type(tex,MonadoForgeTexture)
		self._textures.append(tex)
	
	@property
	def extraData(self):
		return self._extraData
	@extraData.setter
	def extraData(self,value):
		self.clearExtraData()
		for ex in value:
			self.addExtraData(ex)
	def clearExtraData(self):
		self._extraData = []
	def addExtraData(self,ex):
		ensure_type(ex,float)
		self._extraData.append(ex)
	
	@property
	def colourLayerCount(self):
		return self._colourLayerCount
	@colourLayerCount.setter
	def colourLayerCount(self,value):
		ensure_type(value,int)
		self._colourLayerCount = value
	
	@property
	def uvLayerCount(self):
		return self._uvLayerCount
	@uvLayerCount.setter
	def uvLayerCount(self,value):
		ensure_type(value,int)
		self._uvLayerCount = value

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
	
	@property
	def index(self):
		return self._index
	# no setter
	
	@property
	def position(self):
		return self._position
	@position.setter
	def position(self,value):
		ensure_length(value,3)
		self._position = value[:]
	def clearPosition(self):
		self._position = [0,0,0]
	
	@property
	def loops(self):
		return self._loops
	# no setter, for now anyway
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
	
	@property
	def normal(self):
		return self._normal
	@normal.setter
	def normal(self,value):
		ensure_length(value,3)
		self._normal = value[:]
	def clearNormal(self):
		self._normal = None
	@property
	def hasNormal(self):
		return self._normal != None
	# no setter
	
	@property
	def uvs(self):
		return self._uvs
	# no @setter (requires layer)
	def setUV(self,layer,uv):
		ensure_length(uv,2)
		self._uvs[layer] = uv
	def clearUVs(self):
		self._uvs = {}
	@property
	def hasUVs(self):
		return self._uvs != {}
	# no setter
	
	@property
	def colours(self):
		return self._colours
	# no @setter (requires layer)
	def setColour(self,layer,colour):
		ensure_length(colour,4) # Blender really pushes alpha for everything
		self._colours[layer] = colour[:]
	def clearColours(self):
		self._colours = []
	@property
	def hasColours(self):
		return self._colours != {}
	# no setter
	
	@property
	def weightSetIndex(self):
		return self._weightSetIndex
	@weightSetIndex.setter
	def weightSetIndex(self,value):
		ensure_type(value,int)
		self._weightSetIndex = value
	def clearWeightSetIndex(self):
		self._weightSetIndex = -1
	@property
	def hasWeightIndex(self):
		return self._weightSetIndex != -1
	# no setter
	
	@property
	def weights(self):
		return self._weights
	# no @setter (requires group index)
	def setWeight(self,groupIndex,weight):
		ensure_type(weight,float)
		self._weights[groupIndex] = weight
	def clearWeights(self):
		self._weights = {}
	@property
	def hasWeights(self):
		return self._weights != {}
	# no setter
	
	def isDouble(self,other):
		return self == other or (
			self._position == other._position and
			self._weightSetIndex == other._weightSetIndex and
			self._weights == other._weights and
			self._normal == other._normal and
			self._uvs == other._uvs and
			self._colours == other._colours
		)

class MonadoForgeFace:
	def __init__(self,i):
		self._index = i
		self._vertexIndexes = []
		self._materialIndex = 0
	
	@property
	def index(self):
		return self._index
	# no setter
	
	@property
	def vertexIndexes(self):
		return self._vertexIndexes
	@vertexIndexes.setter
	def vertexIndexes(self,value):
		self.clearVertexIndexes()
		for v in value:
			self.addVertexIndex(v)
	def clearVertexIndexes(self):
		self._vertexIndexes = []
	def addVertexIndex(self,v):
		ensure_type(v,int)
		self._vertexIndexes.append(v)

# the fact that the official API has to explain that "loop" means "face corner" tells us how bad even they think the term is
# but it's probably better to just use it than to make something else up just for this add-on
class MonadoForgeLoop:
	def __init__(self,v,f):
		self._vertex = v
		self._face = f
		self._normal = None
		self._uvs = {}
		self._colours = {} # in 255 format
	
	@property
	def vertex(self):
		return self._vertex
	# no setter
	
	@property
	def face(self):
		return self._face
	# no setter
	
	@property
	def normal(self):
		return self._normal
	@normal.setter
	def normal(self,value):
		ensure_length(value,3)
		self._normal = value[:]
	def clearNormal(self):
		self._normal = None
	@property
	def hasNormal(self):
		return self._normal != None
	# no setter
	
	@property
	def uvs(self):
		return self._uvs
	# no @setter (requires layer)
	def setUV(self,layer,uv):
		ensure_length(uv,2)
		self._uvs[layer] = uv
	def clearUVs(self):
		self._uvs = {}
	@property
	def hasUVs(self):
		return self._uvs != {}
	# no setter
	
	@property
	def colours(self):
		return self._colours
	# no @setter (requires layer)
	def setColour(self,layer,colour):
		ensure_length(colour,4) # Blender really pushes alpha for everything
		self._colours[layer] = colour[:]
	def clearColours(self):
		self._colours = []
	@property
	def hasColours(self):
		return self._colours != {}
	# no setter

class MonadoForgeMeshShape:
	def __init__(self):
		self._vertexTableIndex = 0
		self._vertices = {} # indexes are not necessarily in order or sequential, so must be a dict (by index) rather than a plain list
		self._name = ""
	
	@property
	def vertexTableIndex(self):
		return self._vertexTableIndex
	@vertexTableIndex.setter
	def vertexTableIndex(self,value):
		ensure_type(value,int)
		self._vertexTableIndex = value
	
	@property
	def vertices(self):
		return self._vertices
	# no @setter (requires table index)
	def setVertex(self,i,v):
		ensure_type(v,MonadoForgeVertex)
		self._vertices[i] = v
	def clearVertices(self):
		self._vertices = {}
	
	@property
	def name(self):
		return self._name
	@name.setter
	def name(self,value):
		ensure_type(value,str)
		self._name = value

class MonadoForgeMesh:
	def __init__(self):
		self._name = ""
		self._vertices = []
		self._faces = []
		self._weightSets = [] # because it can be convenient to hold these here and have vertexes just refer with index
		self._shapes = [] # list of MonadoForgeMeshShapes
		self._materialIndex = -1
	
	@property
	def name(self):
		return self._name
	@name.setter
	def name(self,value):
		ensure_type(value,str)
		self._name = value
	
	@property
	def vertices(self):
		return self._vertices
	@vertices.setter
	def vertices(self,value):
		self.clearVertices()
		for v in value:
			self.addVertex(v)
	def clearVertices(self):
		self._vertices = []
	def addVertex(self,v):
		ensure_type(v,MonadoForgeVertex)
		self._vertices.append(v)
	
	@property
	def faces(self):
		return self._faces
	@faces.setter
	def faces(self,value):
		self.clearFaces()
		for f in value:
			self.addFace(f)
	def clearFaces(self):
		self._faces = []
	def addFace(self,f):
		ensure_type(f,MonadoForgeFace)
		self._faces.append(f)
	
	@property
	def weightSets(self):
		return self._weightSets
	@weightSets.setter
	def weightSets(self,value):
		self.clearWeightSets()
		for ws in value:
			self.addWeightSet(ws)
	def clearWeightSets(self):
		self._weightSets = []
	def addWeightSet(self,ws):
		ensure_type(ws,list) # can be any length
		self._weightSets.append(ws)
	
	@property
	def shapes(self):
		return self._shapes
	@shapes.setter
	def shapes(self,value):
		self.clearShapes()
		for s in value:
			self.addShape(s)
	def clearShapes(self):
		self._shapes = []
	def addShape(self,shape):
		ensure_type(shape,MonadoForgeMeshShape)
		self._shapes.append(shape)
	
	@property
	def materialIndex(self):
		return self._materialIndex
	@materialIndex.setter
	def materialIndex(self,value):
		ensure_type(value,int)
		self._materialIndex = value
	
	# assumption: if a single vertex has any of these, all the other vertices must also\
	# too potentially expensive to be reasonable @properties
	def hasUVs(self):
		for v in self._vertices:
			if v.hasUVs: return True
		return False
	def hasNormals(self):
		for v in self._vertices:
			if v.hasNormal: return True
		return False
	def hasColours(self):
		for v in self._vertices:
			if v.hasColours: return True
		return False
	def hasWeightIndexes(self):
		for v in self._vertices:
			if v.hasWeightIndex: return True
		return False
	def hasWeights(self):
		for v in self._vertices:
			if v.hasWeights: return True
		return False
	def hasShapes(self):
		return len(self._shapes) > 0
	
	def getVertexPositionsList(self):
		return [v.position for v in self._vertices]
	def getUVLayerList(self):
		layers = []
		for v in self._vertices:
			layers += [k for k in v.uvs.keys()]
		return list(set(layers))
	def getVertexUVsLayer(self,layer):
		return [v.uvs[layer] for v in self._vertices]
	def getVertexNormalsList(self):
		return [v.normal for v in self._vertices]
	def getColourLayerList(self):
		layers = []
		for v in self._vertices:
			layers += [k for k in v.colours.keys()]
		return list(set(layers))
	def getVertexColoursLayer(self,layer):
		return [v.colours[layer] for v in self._vertices]
	def getVertexWeightIndexesList(self):
		return [v.weightSetIndex for v in self._vertices]
	def getVertexWeightsList(self):
		return [v.weights for v in self._vertices]
	def getVertexesInWeightGroup(self,groupID):
		return [v for v in self._vertices if groupID in v.weights.keys()]
	def getVertexesWithWeightIndex(self,index):
		return [v for v in self._vertices if v.weightSetIndex == index]
	def getFaceVertexIndexesList(self):
		return [f.vertexIndexes for f in self._faces]

class MonadoForgeMeshHeader:
	# intended to be immutable, so no setters
	def __init__(self,id,mf1,mf2,vt,ft,mm,lod):
		self._meshID = id
		self._meshFlags1 = mf1
		self._meshFlags2 = mf2
		self._meshVertTableIndex = vt
		self._meshFaceTableIndex = ft
		self._meshMaterialIndex = mm
		self._meshLODValue = lod
	@property
	def meshID(self):
		return self._meshID
	@property
	def meshFlags1(self):
		return self._meshFlags1
	@property
	def meshFlags2(self):
		return self._meshFlags2
	@property
	def meshVertTableIndex(self):
		return self._meshVertTableIndex
	@property
	def meshFaceTableIndex(self):
		return self._meshFaceTableIndex
	@property
	def meshMaterialIndex(self):
		return self._meshMaterialIndex
	@property
	def meshLODValue(self):
		return self._meshLODValue

# this class is specifically for passing wimdo results to wismt import
# assumption: there can only be one skeleton from the .wimdo and a second from an external source (i.e. an .arc/.chr file)
class MonadoForgeWimdoPackage:
	# intended to be immutable, so no setters
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
	@property
	def skeleton(self):
		return self._skeleton
	@property
	def externalSkeleton(self):
		return self._externalSkeleton
	@property
	def meshHeaders(self):
		return self._meshHeaders
	@property
	def shapeHeaders(self):
		return self._shapeHeaders
	@property
	def materials(self):
		return self._materials
	
	# not @properties, can be expensive
	def getLODList(self):
		lods = []
		for mh in self._meshHeaders:
			lods.append(mh.meshLODValue)
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
	
	@property
	def skeleton(self):
		return self._skeleton
	@skeleton.setter
	def skeleton(self,value):
		ensure_type(value,MonadoForgeSkeleton)
		self._skeleton = value
	
	@property
	def externalSkeleton(self):
		return self._externalSkeleton
	@externalSkeleton.setter
	def externalSkeleton(self,value):
		ensure_type(value,MonadoForgeSkeleton)
		self._externalSkeleton = value
	
	@property
	def meshes(self):
		return self._meshes
	@meshes.setter
	def meshes(self,value):
		self.clearMeshes()
		for m in value:
			self.addMesh(m)
	def clearMeshes(self):
		self._meshes = []
	def addMesh(self,mesh):
		ensure_type(mesh,MonadoForgeMesh)
		self._meshes.append(mesh)
	
	@property
	def materials(self):
		return self._materials
	@materials.setter
	def materials(self,value):
		self.clearMaterials()
		for m in value:
			self.addMaterial(m)
	def clearMaterials(self):
		self._materials = []
	def addMaterial(self,material):
		ensure_type(material,MonadoForgeMaterial)
		self._materials.append(material)

def register():
	pass

def unregister():
	pass

#[...]