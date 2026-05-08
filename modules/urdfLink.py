import math
from dataclasses import dataclass

_CM_TO_M = 0.01
_KGCM2_TO_KGM2 = _CM_TO_M ** 2


@dataclass
class Naming:
    component: str
    link: str


@dataclass
class Point3:
    x: float
    y: float
    z: float


@dataclass
class RPY:
    r: float
    p: float
    y: float


@dataclass
class Inertia:
    xx: float
    xy: float
    xz: float
    yy: float
    yz: float
    zz: float


@dataclass
class URDFLink:
    naming: Naming
    mass: float
    origin: Point3
    rotation: RPY
    center_of_mass: Point3
    inertia: Inertia
    material: str = None
    collision_mode: str = None  # None | 'same' | 'custom'


def collectLinksData(link_names, base_link):
    base = _collectLinkData(base_link, 'base_link')
    rest = sorted(
        [_collectLinkData(occ, name) for name, occ in link_names.items() if occ is not base_link],
        key=lambda lnk: lnk.naming.link
    )
    return [base] + rest


def _collectLinkData(occ, link_name):
    m = occ.transform.asArray()
    rotation = _extractRPY(m, occ.name)

    tf = occ.transform.translation
    origin = Point3(tf.x * _CM_TO_M, tf.y * _CM_TO_M, tf.z * _CM_TO_M)

    props = occ.component.physicalProperties
    mass = props.mass

    com = props.centerOfMass
    center_of_mass = Point3(com.x * _CM_TO_M, com.y * _CM_TO_M, com.z * _CM_TO_M)

    (_, xx, yy, zz, xy, yz, xz) = props.getXYZMomentsOfInertia()
    ixx, iyy, izz, ixy, iyz, ixz = [v * _KGCM2_TO_KGM2 for v in [xx, yy, zz, xy, yz, xz]]

    x, y, z = center_of_mass.x, center_of_mass.y, center_of_mass.z
    offsets = [y**2 + z**2, x**2 + z**2, x**2 + y**2, -x*y, -y*z, -x*z]
    ixx, iyy, izz, ixy, iyz, ixz = [
        i - mass * d for i, d in zip([ixx, iyy, izz, ixy, iyz, ixz], offsets)
    ]
    inertia = Inertia(ixx, ixy, ixz, iyy, iyz, izz)

    return URDFLink(
        Naming(occ.name, link_name),
        mass,
        origin,
        rotation,
        center_of_mass,
        inertia,
        collision_mode=_detectCollisionMode(occ.component),
    )


def _detectCollisionMode(component):
    for body in component.bRepBodies:
        if body.name == 'urdfCollision':
            return 'custom'
        if body.name == 'urdfSameCollision':
            return 'same'
    return None


def _extractRPY(m, name):
    r00, r01, r02 = m[0], m[1], m[2]
    r10, r11, r12 = m[4], m[5], m[6]
    r20, r21, r22 = m[8], m[9], m[10]

    sin_pitch = max(-1.0, min(1.0, -r20))
    pitch = math.asin(sin_pitch)
    cos_pitch = math.cos(pitch)

    if abs(cos_pitch) > 1e-6:
        roll = math.atan2(r21, r22)
        yaw = math.atan2(r10, r00)
    else:
        roll = 0.0
        yaw = math.atan2(-r01, r11)

    return RPY(roll, pitch, yaw)
