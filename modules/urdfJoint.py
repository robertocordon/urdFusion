import math
import adsk.core
import adsk.fusion
from dataclasses import dataclass

_CM_TO_M = 0.01
_DEFAULT_EFFORT = 100.0
_DEFAULT_VELOCITY = 100.0


@dataclass
class JointData:
    name: str
    urdf_type: str       # 'fixed', 'revolute', 'continuous', 'prismatic'
    parent_link: str
    child_link: str
    origin_xyz: tuple    # (x, y, z) meters, child frame origin in parent frame
    origin_rpy: tuple    # (r, p, y) radians
    axis: tuple          # (x, y, z) unit vector in joint frame; None for fixed
    lower: float         # limit in rad or m; None if not applicable
    upper: float
    effort: float        # None for fixed/continuous
    velocity: float


def collectJointsData(link_names, base_link):
    """
    Returns (joints, child_visual_origins) where:
      joints:               list of JointData in BFS order from base_link
      child_visual_origins: {link_name: (xyz_tuple, rpy_tuple)}
                            visual origin for each child link in its joint frame
    """
    design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    occ_map = _buildOccMap(link_names, base_link)
    name_map = {occ.name: tok for tok, (_, occ) in occ_map.items()}
    relevant = _gatherRelevantJoints(design, occ_map, name_map)
    tree_edges = _bfsTree(base_link, relevant, occ_map)

    joints = []
    child_visual_origins = {}

    for parent_token, child_token, joint in tree_edges:
        parent_name, parent_occ = occ_map[parent_token]
        child_name, child_occ = occ_map[child_token]
        jdata, vis = _buildJointData(joint, parent_name, parent_occ, child_name, child_occ)
        if jdata is not None:
            joints.append(jdata)
            child_visual_origins[child_name] = vis

    return joints, child_visual_origins


def _buildOccMap(link_names, base_link):
    m = {base_link.entityToken: ('base_link', base_link)}
    for name, occ in link_names.items():
        if occ is not base_link:
            m[occ.entityToken] = (name, occ)
    return m


def _gatherRelevantJoints(design, occ_map, name_map):
    """Returns list of (joint, link_token_1, link_token_2)."""
    seen = set()
    relevant = []

    all_components = [design.rootComponent]
    for occ in design.rootComponent.allOccurrences:
        all_components.append(occ.component)

    for comp in all_components:
        for joint in list(comp.joints) + list(comp.asBuiltJoints):
            if joint.name in seen:
                continue
            seen.add(joint.name)
            o1 = joint.occurrenceOne
            o2 = joint.occurrenceTwo
            if o1 is None or o2 is None:
                continue
            t1 = _findContainingLinkToken(o1, occ_map, name_map)
            t2 = _findContainingLinkToken(o2, occ_map, name_map)
            if t1 is not None and t2 is not None and t1 != t2:
                relevant.append((joint, t1, t2))
    return relevant


def _findContainingLinkToken(occ, occ_map, name_map):
    """Walk up the occurrence hierarchy to find the ancestor that is a selected link."""
    current = occ
    while current is not None:
        try:
            tok = current.entityToken
            if tok in occ_map:
                return tok
        except Exception:
            pass
        if current.name in name_map:
            return name_map[current.name]
        current = current.assemblyContext
    return None


def _bfsTree(base_link, relevant, occ_map):
    base_token = base_link.entityToken
    visited = {base_token}
    queue = [base_token]
    edges = []

    adj = {}
    for joint, t1, t2 in relevant:
        adj.setdefault(t1, []).append((joint, t2))
        adj.setdefault(t2, []).append((joint, t1))

    while queue:
        cur = queue.pop(0)
        for joint, nbr in adj.get(cur, []):
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)
                edges.append((cur, nbr, joint))

    return edges


def _buildJointData(joint, parent_name, parent_occ, child_name, child_occ):
    motion = joint.jointMotion
    jtype = motion.jointType
    JT = adsk.fusion.JointTypes

    if jtype == JT.RigidJointType:
        urdf_type = 'fixed'
    elif jtype == JT.RevoluteJointType:
        urdf_type = 'revolute'
    elif jtype == JT.SliderJointType:
        urdf_type = 'prismatic'
    elif jtype == JT.CylindricalJointType:
        urdf_type = 'revolute'  # cylindrical = revolute + prismatic; ignore translation
    else:
        return None, None  # PinSlot, Planar, Ball not supported

    pm = _parseTransform(parent_occ.transform.asArray())
    cm = _parseTransform(child_occ.transform.asArray())

    # Joint frame orientation = child component orientation
    # origin rpy = rotation of child component frame in parent component frame
    rel_rot = _matMul(pm['rT'], cm['r'])
    origin_rpy = _matToRPY(rel_rot)

    if urdf_type == 'fixed':
        joint_world = cm['t']
        axis = None
        lower = upper = effort = velocity = None
    else:
        joint_world = _getJointOriginWorld(joint, child_occ)
        axis_world = _getAxisWorld(motion)
        # Express axis in joint frame (= child component frame)
        axis = _mulRV(cm['rT'], axis_world)

        if jtype in (JT.RevoluteJointType, JT.CylindricalJointType):
            lims = motion.rotationLimits
            if lims.isMinimumValueEnabled and lims.isMaximumValueEnabled:
                lower, upper = lims.minimumValue, lims.maximumValue
                effort, velocity = _DEFAULT_EFFORT, _DEFAULT_VELOCITY
            else:
                urdf_type = 'continuous'
                lower = upper = effort = velocity = None
        else:  # prismatic
            lims = motion.slideLimits
            if lims.isMinimumValueEnabled and lims.isMaximumValueEnabled:
                lower = lims.minimumValue * _CM_TO_M
                upper = lims.maximumValue * _CM_TO_M
            else:
                lower, upper = -1e6, 1e6
            effort, velocity = _DEFAULT_EFFORT, _DEFAULT_VELOCITY

    # Joint origin xyz: joint world point expressed in parent frame (cm → m)
    origin_xyz = tuple(v * _CM_TO_M for v in _worldToLocal(pm, joint_world))

    # Visual origin for child: child component origin relative to joint frame
    # Joint frame has origin=joint_world and orientation=child component
    diff = tuple(cm['t'][i] - joint_world[i] for i in range(3))
    vis_xyz = tuple(v * _CM_TO_M for v in _mulRV(cm['rT'], diff))

    return JointData(
        name=joint.name,
        urdf_type=urdf_type,
        parent_link=parent_name,
        child_link=child_name,
        origin_xyz=origin_xyz,
        origin_rpy=origin_rpy,
        axis=axis,
        lower=lower,
        upper=upper,
        effort=effort,
        velocity=velocity,
    ), (vis_xyz, (0.0, 0.0, 0.0))


def _getJointOriginWorld(joint, child_occ):
    """Returns joint geometry origin in root component (world) coordinates, cm."""
    try:
        if isinstance(joint, adsk.fusion.AsBuiltJoint):
            o = joint.geometry.origin
        else:
            o = joint.geometryOrOriginTwo.origin
        if o is not None:
            return (o.x, o.y, o.z)
    except Exception:
        pass
    t = child_occ.transform.translation
    return (t.x, t.y, t.z)


def _getAxisWorld(motion):
    """Returns joint axis as unit vector in root component (world) coordinates."""
    try:
        if hasattr(motion, 'rotationAxisVector'):
            v = motion.rotationAxisVector
        else:
            v = motion.slideDirectionVector
        return (v.x, v.y, v.z)
    except Exception:
        return (0.0, 0.0, 1.0)


def _parseTransform(m):
    r = [[m[0], m[1], m[2]],
         [m[4], m[5], m[6]],
         [m[8], m[9], m[10]]]
    rT = [[r[j][i] for j in range(3)] for i in range(3)]
    return {'r': r, 'rT': rT, 't': (m[3], m[7], m[11])}


def _matMul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


def _matToRPY(r):
    sp = max(-1.0, min(1.0, -r[2][0]))
    p = math.asin(sp)
    cp = math.cos(p)
    if abs(cp) > 1e-6:
        roll = math.atan2(r[2][1], r[2][2])
        yaw = math.atan2(r[1][0], r[0][0])
    else:
        roll = 0.0
        yaw = math.atan2(-r[0][1], r[1][1])
    return (roll, p, yaw)


def _mulRV(rT, v):
    return tuple(sum(rT[i][k] * v[k] for k in range(3)) for i in range(3))


def _worldToLocal(fm, world_pt):
    diff = tuple(world_pt[i] - fm['t'][i] for i in range(3))
    return _mulRV(fm['rT'], diff)
