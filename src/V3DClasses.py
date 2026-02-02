import numpy as np
import math


class Vector3:
    def __init__(self, x=0, y=0, z=0):
        self.x, self.y, self.z = x, y, z

    def set(self, x, y, z):
        self.x, self.y, self.z = x, y, z
        return self

    def get(self):
        return self.x, self.y, self.z

    def copy(self, v):
        self.x, self.y, self.z = v.x, v.y, v.z
        return self

    def addScaledVector(self, v, s):
        self.x += v.x * s
        self.y += v.y * s
        self.z += v.z * s
        return self

    def applyMatrix4(self, m):
        v = np.array([self.x, self.y, self.z, 1.0])
        r = m.elements @ v
        self.x, self.y, self.z = r[:3]
        return self

    def fromBufferAttribute(self, attr, index):
        i = index * attr.itemSize
        self.x, self.y, self.z = attr.array[i:i+3]
        return self

class Vector4:
    def __init__(self, x=0, y=0, z=0, w=0):
        self.x, self.y, self.z, self.w = x, y, z, w

    def set(self, x, y, z, w):
        self.x, self.y, self.z, self.w = x, y, z, w
        return self

    def multiplyScalar(self, s):
        self.x *= s
        self.y *= s
        self.z *= s
        self.w *= s
        return self

    def manhattanLength(self):
        return abs(self.x) + abs(self.y) + abs(self.z) + abs(self.w)

    def getComponent(self, i):
        return [self.x, self.y, self.z, self.w][i]

    def fromBufferAttribute(self, attr, index):
        i = index * attr.itemSize
        self.x, self.y, self.z, self.w = attr.array[i:i+4]
        return self

class Matrix4:
    def __init__(self):
        self.elements = np.identity(4, dtype=np.float32)

    def copy(self, m):
        self.elements[:] = m.elements
        return self

    def multiply(self, m):
        self.elements = self.elements @ m.elements
        return self

    def multiplyMatrices(self, a, b):
        self.elements = a.elements @ b.elements
        return self

    def getInverse(self, m):
        self.elements = np.linalg.inv(m.elements)
        return self

    def toArray(self, array, offset=0):
        array[offset:offset+16] = self.elements.flatten()

    def fromArray(self, array, offset=0):
        self.elements[:] = np.array(array[offset:offset+16]).reshape((4,4))
        return self

    def decompose(self, position, quaternion, scale):
        position.x, position.y, position.z = self.elements[:3, 3]
        scale.x = np.linalg.norm(self.elements[:3, 0])
        scale.y = np.linalg.norm(self.elements[:3, 1])
        scale.z = np.linalg.norm(self.elements[:3, 2])

class Object3D:
    def __init__(self):
        self.parent = None
        self.children = []

        self.position = Vector3()
        self.rotation = Vector3()  # radians
        self.scale = Vector3(1, 1, 1)

        self.matrix = Matrix4()
        self.matrixWorld = Matrix4()

    def add(self, child):
        if child.parent:
            child.parent.children.remove(child)

        child.parent = self
        self.children.append(child)

    def updateMatrix(self):
        m = np.identity(4, dtype=np.float32)
        m[0, 3] = self.position.x
        m[1, 3] = self.position.y
        m[2, 3] = self.position.z
        self.matrix.elements[:] = m

    def updateMatrixWorld(self, force=False):
        self.updateMatrix()

        if self.parent:
            self.matrixWorld.multiplyMatrices(
                self.parent.matrixWorld,
                self.matrix
            )
        else:
            self.matrixWorld.copy(self.matrix)

        for child in self.children:
            child.updateMatrixWorld(force)



class BufferAttribute:
    def __init__(self, array, itemSize):
        self.array = np.array(array, dtype=np.float32)
        self.itemSize = itemSize
        self.count = len(self.array) // itemSize

    def getX(self, i): return self.array[i*self.itemSize]
    def getY(self, i): return self.array[i*self.itemSize+1]
    def getZ(self, i): return self.array[i*self.itemSize+2]
    def getW(self, i): return self.array[i*self.itemSize+3]

    def setXYZW(self, i, x, y, z, w):
        idx = i * self.itemSize
        self.array[idx:idx+4] = [x, y, z, w]


class Geometry:
    def __init__(self):
        self.attributes = {}

class Material:
    def __init__(self, texture, vertex_color):
        self.texture = texture
        self.vertex_color = vertex_color

class Mesh(Object3D):
    def __init__(self, geometry=None, material=None):
        super().__init__()
        self.geometry = geometry
        self.material = material


class SkinnedMesh(Mesh):
    def __init__(self, geometry, material):
        super().__init__(geometry, material)
        self.bindMatrix = Matrix4()
        self.bindMatrixInverse = Matrix4()
        self.bindMode = "attached"
        self.skeleton = None

    def bind(self, skeleton):
        self.skeleton = skeleton
        self.updateMatrixWorld(True)
        self.bindMatrix.copy(self.matrixWorld)
        self.bindMatrixInverse.getInverse(self.bindMatrix)

    def boneTransform(self, index, target):
        base = Vector3().fromBufferAttribute(
            self.geometry.attributes["position"], index
        ).applyMatrix4(self.bindMatrix)

        skinIndex = Vector4().fromBufferAttribute(
            self.geometry.attributes["skinIndex"], index
        )
        skinWeight = Vector4().fromBufferAttribute(
            self.geometry.attributes["skinWeight"], index
        )

        target.set(0, 0, 0)

        for i in range(4):
            w = skinWeight.getComponent(i)
            if w != 0:
                bi = int(skinIndex.getComponent(i))
                m = Matrix4().multiplyMatrices(
                    self.skeleton.bones[bi].matrixWorld,
                    self.skeleton.boneInverses[bi]
                )
                target.addScaledVector(
                    Vector3().copy(base).applyMatrix4(m), w
                )

        return target.applyMatrix4(self.bindMatrixInverse)

class MPDGeometry:
    def __init__(self, positions, normals, colors, uvs, indices):
        self.positions = positions
        self.normals = normals
        self.colors = colors
        self.uvs = uvs
        self.indices = indices



_identityMatrix = Matrix4()
_offsetMatrix = Matrix4()


class Skeleton:
    def __init__(self, bones=None, boneInverses=None):
        self.bones = list(bones) if bones else []
        self.boneMatrices = [0.0] * (len(self.bones) * 16)
        self.frame = -1

        if boneInverses is None:
            self.calculateInverses()
        else:
            if len(boneInverses) == len(self.bones):
                self.boneInverses = list(boneInverses)
            else:
                print("Skeleton boneInverses is the wrong length.")
                self.boneInverses = [Matrix4() for _ in self.bones]

        self.boneTexture = None

    def calculateInverses(self):
        self.boneInverses = []

        for bone in self.bones:
            inverse = Matrix4()
            if bone:
                inverse.getInverse(bone.matrixWorld)
            self.boneInverses.append(inverse)

    def pose(self):
        # restore bind pose world matrices
        for i, bone in enumerate(self.bones):
            if bone:
                bone.matrixWorld.getInverse(self.boneInverses[i])

        # compute local transforms
        for bone in self.bones:
            if bone:
                if bone.parent and getattr(bone.parent, "isBone", False):
                    bone.matrix.getInverse(bone.parent.matrixWorld)
                    bone.matrix.multiply(bone.matrixWorld)
                else:
                    bone.matrix.copy(bone.matrixWorld)

                bone.matrix.decompose(
                    bone.position, bone.quaternion, bone.scale
                )

    def update(self):
        for i, bone in enumerate(self.bones):
            matrix = bone.matrixWorld if bone else _identityMatrix
            _offsetMatrix.multiplyMatrices(matrix, self.boneInverses[i])
            _offsetMatrix.toArray(self.boneMatrices, i * 16)

        if self.boneTexture:
            self.boneTexture.needsUpdate = True

    def clone(self):
        return Skeleton(self.bones, self.boneInverses)

    def getBoneByName(self, name):
        for bone in self.bones:
            if bone and bone.name == name:
                return bone
        return None

    def dispose(self):
        if self.boneTexture:
            self.boneTexture.dispose()
            self.boneTexture = None


class Bone(Object3D):
    def __init__(self):
        super().__init__()
        self.type = "Bone"
        self.isBone = True
        self.name = ""