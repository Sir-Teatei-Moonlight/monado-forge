# because just packing/unpacking arrays gets old and error-prone

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

# this class is specifically for keeping hold of wimdo data to be passed to a wismt
class MonadoForgeWimdoMaterial:
	def __init__(self,i):
		self._index = i
		self._name = "Material"
		self._baseColour = [1.0,1.0,1.0,1.0]
		self._textureTable = [] # [[id,???,???,???]]
		self._textureMirrorFlags = 0
		self._extraData = []
		self._extraDataIndex = 0 # needed because of how extra data needs to be read separately
	
	# no setter (index should be immutable)
	def getIndex(self):
		return self._index
	
	def getName(self):
		return self._name
	def setName(self,x):
		if not isinstance(x,str):
			raise TypeError("expected a string, not a(n) "+str(type(x)))
		self._name = x
	
	def getBaseColour(self):
		return self._baseColour
	def setBaseColour(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._baseColour = a[:]
	
	def getTextureTable(self):
		return self._textureTable
	def clearTextureTable(self):
		self._textureTable = []
	def addTextureTableItem(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._textureTable.append(a)
	def setTextureTable(self,ts):
		if not isinstance(ts,list):
			raise TypeError("expected a list, not a(n) "+str(type(ts)))
		for t in ts: self.addTextureTableItem(t)
	
	def getTextureMirrorFlags(self):
		return self._textureMirrorFlags
	def setTextureMirrorFlags(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._textureMirrorFlags = x
	
	def getExtraData(self):
		return self._extraData
	def clearExtraData(self):
		self._extraData = []
	def addExtraData(self,ex):
		if not isinstance(ex,float):
			raise TypeError("expected a float, not a(n) "+str(type(ex)))
		self._extraData.append(ex)
	def setExtraData(self,exs):
		self.clearExtraData()
		for ex in exs: self.addExtraData(ex)
	
	def getExtraDataIndex(self):
		return self._extraDataIndex
	def setExtraDataIndex(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._extraDataIndex = x

class MonadoForgeTexture:
	def __init__(self):
		self._name = "Texture"
		self._mirroring = [False,False]
	
	def getName(self):
		return self._name
	def setName(self,x):
		if not isinstance(x,str):
			raise TypeError("expected a string, not a(n) "+str(type(x)))
		self._name = x
	
	def getMirroring(self):
		return self._mirroring
	def setMirroring(self,a):
		if len(a) != 2:
			raise ValueError("sequence must be length 2, not "+str(len(a)))
		self._mirroring = a[:]

class MonadoForgeMaterial:
	def __init__(self,i):
		self._index = i
		self._name = "Material"
		self._baseColour = [1.0,1.0,1.0,1.0]
		self._viewportColour = [0.5,0.5,0.5,1.0]
		self._textures = []
		self._extraData = []
		self._uvLayerCount = 0 # not actually part of the material, but the material needs to know
	
	# no setter (index should be immutable)
	def getIndex(self):
		return self._index
	
	def getName(self):
		return self._name
	def setName(self,x):
		if not isinstance(x,str):
			raise TypeError("expected a string, not a(n) "+str(type(x)))
		self._name = x
	
	def getBaseColour(self):
		return self._baseColour
	def setBaseColour(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._baseColour = a[:]
	
	def getViewportColour(self):
		return self._viewportColour
	def setViewportColour(self,a):
		if len(a) != 4:
			raise ValueError("sequence must be length 4, not "+str(len(a)))
		self._viewportColour = a[:]
	
	def getTextures(self):
		return self._textures
	def clearTextures(self):
		self._textures = []
	def addTexture(self,x):
		if not isinstance(x,MonadoForgeTexture):
			raise TypeError("expected a MonadoForgeTexture, not a(n) "+str(type(x)))
		self._textures.append(x)
	def setTextures(self,a):
		self.clearTextures()
		for x in a: self.addTexture(x)
	
	def getExtraData(self):
		return self._extraData
	def clearExtraData(self):
		self._extraData = []
	def addExtraData(self,ex):
		if not isinstance(ex,float):
			raise TypeError("expected a float, not a(n) "+str(type(ex)))
		self._extraData.append(ex)
	def setExtraData(self,exs):
		self.clearExtraData()
		for ex in exs: self.addExtraData(ex)
	
	def getUVLayerCount(self):
		return self._uvLayerCount
	def setUVLayerCount(self,x):
		if not isinstance(x,int):
			raise TypeError("expected an int, not a(n) "+str(type(x)))
		self._uvLayerCount = x

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
		self._weightSets = [] # because it can be convenient to hold these here and have vertexes just refer with index
		self._shapes = [] # list of MonadoForgeMeshShapes
		self._materialIndex = 0
	
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
	def addWeightSet(self,a):
		if not isinstance(a,list):
			raise TypeError("expected a list, not a(n) "+str(type(a)))
		self._weightSets.append(a)
	def setWeightSets(self,d):
		if not isinstance(d,list):
			raise TypeError("expected a list, not a(n) "+str(type(d)))
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
	
	def getMaterialIndex(self):
		return self._materialIndex
	def setMaterialIndex(self,i):
		if not isinstance(i,int):
			raise TypeError("expected an int, not a(n) "+str(type(i)))
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
	def getVertexesWithWeightIndex(self,index):
		return [v for v in self._vertices if v.getWeightSetIndex() == index]
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
# assumption: there can only be one skeleton from the .wimdo and a second from an external source (i.e. an .arc/.chr file)
class MonadoForgeWimdoPackage:
	def __init__(self,skel,skelEx,mh,sh,mat):
		if not isinstance(skel,MonadoForgeSkeleton):
			raise TypeError("expected a MonadoForgeSkeleton, not a(n) "+str(type(skel)))
		if skelEx and not isinstance(skelEx,MonadoForgeSkeleton):
			raise TypeError("expected a MonadoForgeSkeleton, not a(n) "+str(type(skelEx)))
		if not isinstance(mh,list):
			raise TypeError("expected a list, not a(n) "+str(type(mh)))
		if not isinstance(sh,list):
			raise TypeError("expected a list, not a(n) "+str(type(sh)))
		if not isinstance(mat,list):
			raise TypeError("expected a list, not a(n) "+str(type(mat)))
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