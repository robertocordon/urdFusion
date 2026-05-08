import re

_INVALID_CHARS = re.compile(r'[^a-z0-9_]')
_MULTI_UNDERSCORE = re.compile(r'_+')
_LEADING_BAD = re.compile(r'^[0-9_]+')


def sanitizeName(name):
    name = name.lower()
    name = _INVALID_CHARS.sub('_', name)
    name = _MULTI_UNDERSCORE.sub('_', name)
    name = _LEADING_BAD.sub('', name)
    return name.rstrip('_')
