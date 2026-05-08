import json
import os

_PATH = os.path.join(os.path.expanduser('~'), '.urdFusion', 'settings.json')


def load():
    try:
        with open(_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save(data):
    try:
        os.makedirs(os.path.dirname(_PATH), exist_ok=True)
        with open(_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
