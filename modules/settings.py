import json
import os
import platform

_KEY_LAST_EXPORT_FOLDER = 'last_export_folder'
_KEY_LAST_BASE_LINK = 'last_base_link'
_KEY_LAST_COLOR_MODE = 'last_color_mode'


def _defaultPath():
    system = platform.system()
    if system == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif system == 'Darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:
        base = os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(base, 'urdFusion', 'settings.json')


_PATH = _defaultPath()


def _load():
    try:
        with open(_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _update(key, value):
    data = _load()
    data[key] = value
    _save(data)


def getLastExportFolder():
    return _load().get(_KEY_LAST_EXPORT_FOLDER, '')


def setLastExportFolder(folder):
    _update(_KEY_LAST_EXPORT_FOLDER, folder)


def getLastBaseLink():
    return _load().get(_KEY_LAST_BASE_LINK, '')


def setLastBaseLink(name):
    _update(_KEY_LAST_BASE_LINK, name)


def getLastColorMode():
    return _load().get(_KEY_LAST_COLOR_MODE, '')


def setLastColorMode(name):
    _update(_KEY_LAST_COLOR_MODE, name)
