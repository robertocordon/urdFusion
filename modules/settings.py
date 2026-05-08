import json
import os
import platform

_KEY_LAST_EXPORT_FOLDER = 'last_export_folder'
_KEY_LAST_BASE_LINK = 'last_base_link'
_KEY_LAST_COLOR_MODE = 'last_color_mode'


def _defaultPath() -> str:
    system = platform.system()
    if system == 'Windows':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif system == 'Darwin':
        base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
    else:
        base = os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(base, 'urdFusion', 'settings.json')


_PATH = _defaultPath()
_cache = None


def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(_PATH, 'r') as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    return _cache


def _save(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _update(key: str, value) -> None:
    _load()  # ensure _cache is populated
    _cache[key] = value
    _save(_cache)


def getLastExportFolder() -> str:
    return _load().get(_KEY_LAST_EXPORT_FOLDER, '')


def setLastExportFolder(folder: str) -> None:
    _update(_KEY_LAST_EXPORT_FOLDER, folder)


def getLastBaseLink() -> str:
    return _load().get(_KEY_LAST_BASE_LINK, '')


def setLastBaseLink(name: str) -> None:
    _update(_KEY_LAST_BASE_LINK, name)


def getLastColorMode() -> str:
    return _load().get(_KEY_LAST_COLOR_MODE, '')


def setLastColorMode(name: str) -> None:
    _update(_KEY_LAST_COLOR_MODE, name)
