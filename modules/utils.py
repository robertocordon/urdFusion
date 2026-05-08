import math
import re

CM_TO_M: float = 0.01
KGCM2_TO_KGM2: float = CM_TO_M ** 2

_INVALID_CHARS = re.compile(r'[^a-z0-9_]')
_MULTI_UNDERSCORE = re.compile(r'_+')
_LEADING_BAD = re.compile(r'^[0-9_]+')


def matToRPY(r):
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


def sanitizeName(name):
    name = name.lower()
    name = _INVALID_CHARS.sub('_', name)
    name = _MULTI_UNDERSCORE.sub('_', name)
    name = _LEADING_BAD.sub('', name)
    return name.rstrip('_')
