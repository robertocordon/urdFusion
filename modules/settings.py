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


def getLastExportFolder():
    return _load().get(_KEY_LAST_EXPORT_FOLDER, '')


def setLastExportFolder(folder):
    data = _load()
    data[_KEY_LAST_EXPORT_FOLDER] = folder
    _save(data)


def getLastBaseLink():
    return _load().get(_KEY_LAST_BASE_LINK, '')


def setLastBaseLink(name):
    data = _load()
    data[_KEY_LAST_BASE_LINK] = name
    _save(data)


def getLastColorMode():
    return _load().get(_KEY_LAST_COLOR_MODE, '')


def setLastColorMode(name):
    data = _load()
    data[_KEY_LAST_COLOR_MODE] = name
    _save(data)
