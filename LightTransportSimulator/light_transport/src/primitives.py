from .constants import EPSILON
from .material import Material
from .vectors import normalize
import numpy as np
import numba
import enum


class ShapeOptions(enum.Enum):
    TRIANGLE = 1
    PLANE = 2
    SPHERE = 3
    AABB = 4
    TRIANGLEPC = 5


@numba.experimental.jitclass([
    ('type', numba.intp),
    ('id', numba.intp),
    ('vertex_1', numba.float64[:]),
    ('vertex_2', numba.float64[:]),
    ('vertex_3', numba.float64[:]),
    ('centroid', numba.float64[:]),
    ('material', Material.class_type.instance_type),
    ('is_light', numba.boolean),
    ('normal', numba.float64[:])
])
class Triangle:
    def __init__(self, id, vertex_1, vertex_2, vertex_3, material, is_light=False):
        self.type = ShapeOptions.TRIANGLE.value
        self.id = id
        self.vertex_1 = vertex_1
        self.vertex_2 = vertex_2
        self.vertex_3 = vertex_3
        self.centroid = (vertex_1+vertex_2+vertex_3)/3
        self.material = material
        self.is_light = is_light
        self.normal = normalize(np.cross(vertex_2-vertex_1, vertex_3-vertex_1))


@numba.experimental.jitclass([
    ('type', numba.intp),
    ('center', numba.float64[:]),
    ('radius', numba.float64[:]),
    ('material', Material.class_type.instance_type)
])
class Sphere:
    def __init__(self, center, radius, material):
        self.type = ShapeOptions.SPHERE.value
        self.center = center
        self.radius = radius
        self.material = material


@numba.experimental.jitclass([
    ('type', numba.intp),
    ('point', numba.float64[:]),
    ('normal', numba.float64[:]),
    ('material', Material.class_type.instance_type)
])
class Plane:
    def __init__(self, point, normal, material):
        self.type = ShapeOptions.PLANE.value
        self.point = point
        self.normal = normal
        self.material = material


@numba.experimental.jitclass([
    ('type', numba.intp),
    ('min_point', numba.float64[:]),
    ('max_point', numba.float64[:]),
    ('centroid', numba.float64[:])
])
class AABB:
    def __init__(self, min_point, max_point):
        self.type = ShapeOptions.AABB.value
        self.min_point = min_point
        self.max_point = max_point
        self.centroid = (min_point+max_point)/2


c_1d_vec = numba.types.Array(dtype=numba.float64, ndim=1, layout="C")

@numba.experimental.jitclass([
    ('type', numba.intp),
    ('vertex_1', c_1d_vec),
    ('vertex_2', c_1d_vec),
    ('vertex_3', c_1d_vec),
    ('centroid', c_1d_vec),
    ('material', Material.class_type.instance_type),
    ('is_light', numba.boolean),
    ('edge_1', c_1d_vec),
    ('edge_2', c_1d_vec),
    ('normal', c_1d_vec),
    ('num', numba.float64),
    ('transformation', numba.float64[:,:])
])
class PreComputedTriangle:
    def __init__(self, vertex_1, vertex_2, vertex_3, material, is_light=False):
        self.type = ShapeOptions.TRIANGLEPC.value
        self.vertex_1 = vertex_1
        self.vertex_2 = vertex_2
        self.vertex_3 = vertex_3
        self.centroid = (vertex_1+vertex_2+vertex_3)/3
        self.material = material
        self.is_light = is_light
        self.edge_1 = vertex_2-vertex_1
        self.edge_2 = vertex_3-vertex_1
        _normal = np.cross(self.edge_1[:3], self.edge_2[:3])
        self.normal = np.append(normalize(_normal),0)
        self.num = np.dot(self.vertex_1[:3], _normal)
        self.transformation = np.zeros(shape=(12,1), dtype=np.float64)

        if abs(_normal[0]) > abs(_normal[1])  and  abs(_normal[0]) > abs(_normal[2]):

            x1 = self.vertex_2[1] * self.vertex_1[2] - self.vertex_2[2] * self.vertex_1[1]
            x2 = self.vertex_3[1] * self.vertex_1[2] - self.vertex_3[2] * self.vertex_1[1]

            self.transformation[0] = 0.0
            self.transformation[1] = self.edge_2[2] / _normal[0]
            self.transformation[2] = -self.edge_2[1] / _normal[0]
            self.transformation[3] = x2 / _normal[0]

            self.transformation[4] = 0.0
            self.transformation[5] = -self.edge_1[2] / _normal[0]
            self.transformation[6] = self.edge_1[1] / _normal[0]
            self.transformation[7] = -x1 / _normal[0]

            self.transformation[8] = 1.0
            self.transformation[9] = _normal[1] / _normal[0]
            self.transformation[10] = _normal[2] / _normal[0]
            self.transformation[11] = -self.num / _normal[0]

        elif abs(_normal[1]) > abs(_normal[2]):

            x1 = self.vertex_2[2] * self.vertex_1[0] - self.vertex_2[0] * self.vertex_1[2]
            x2 = self.vertex_3[2] * self.vertex_1[0] - self.vertex_3[0] * self.vertex_1[2]

            self.transformation[0] = -self.edge_2[2] / _normal[1]
            self.transformation[1] = 0.0
            self.transformation[2] = self.edge_2[0] / _normal[1]
            self.transformation[3] = x2 / _normal[1]

            self.transformation[4] = self.edge_1[2] / _normal[1]
            self.transformation[5] = 0.0
            self.transformation[6] = -self.edge_1[0] / _normal[1]
            self.transformation[7] = -x1 / _normal[1]

            self.transformation[8] = _normal[0] / _normal[1]
            self.transformation[9] = 1.0
            self.transformation[10] = _normal[2] / _normal[1]
            self.transformation[11] = -self.num / _normal[1]

        elif abs(_normal[2]) > 0.0:

            x1 = self.vertex_2[0] * self.vertex_1[1] - self.vertex_2[1] * self.vertex_1[0]
            x2 = self.vertex_3[0] * self.vertex_1[1] - self.vertex_3[1] * self.vertex_1[0]

            self.transformation[0] = self.edge_2[1] / _normal[2]
            self.transformation[1] = -self.edge_2[0] / _normal[2]
            self.transformation[2] = 0.0
            self.transformation[3] = x2 / _normal[2]

            self.transformation[4] = -self.edge_1[1] / _normal[2]
            self.transformation[5] = self.edge_1[0] / _normal[2]
            self.transformation[6] = 0.0
            self.transformation[7] = -x1 / _normal[2]

            self.transformation[8] = _normal[0] / _normal[2]
            self.transformation[9] = _normal[1] / _normal[2]
            self.transformation[10] = 1.0
            self.transformation[11] = -self.num / _normal[2]

    def intersect(self, ray):

        # Get barycentric z components of ray origin and direction for calculation of t value
        trans_s = (self.transformation[8] * ray.origin[0] +
                   self.transformation[9] * ray.origin[1] +
                   self.transformation[10] * ray.origin[2] +
                   self.transformation[11])
        trans_d = (self.transformation[8] * ray.direction[0] +
                   self.transformation[9] * ray.direction[1] +
                   self.transformation[10] * ray.direction[2])

        ta = -trans_s / trans_d

        # Reject negative t values and rays parallel to triangle
        if ta <= EPSILON or ta >= ray.tmax:
            return None

        # Get global coordinates of ray's intersection with triangle's plane.
        wr = ray.origin + ta * ray.direction

        # Calculate "x" and "y" barycentric coordinates
        xg = (self.transformation[0] * wr[0] +
              self.transformation[1] * wr[1] +
              self.transformation[2] * wr[2] +
              self.transformation[3])
        yg = (self.transformation[4] * wr[0] +
              self.transformation[5] * wr[1] +
              self.transformation[6] * wr[2] +
              self.transformation[7])

        # final intersection test
        if xg >= 0.0 and yg >= 0.0 and yg + xg < 1.0:
            return ta.item()

        return None


