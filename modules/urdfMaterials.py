import adsk.core
from dataclasses import dataclass

COLOR_MODE_MATERIAL = 'Material Colors'
COLOR_MODE_RAINBOW = 'Rainbow'

_COLORS = [
    ('slate_blue',   (0.180, 0.200, 0.450, 1.0)),
    ('crimson',      (0.550, 0.070, 0.090, 1.0)),
    ('forest_green', (0.130, 0.370, 0.180, 1.0)),
    ('amber',        (0.800, 0.500, 0.050, 1.0)),
    ('steel_gray',   (0.550, 0.570, 0.600, 1.0)),
    ('plum',         (0.450, 0.150, 0.400, 1.0)),
]


@dataclass
class MaterialData:
    name: str
    rgba: tuple


def getAvailableColors():
    return list(_COLORS)


def populateMaterials(links, joints, color_choice, link_names, base_link):
    registry = {}  # name -> rgba

    if color_choice == COLOR_MODE_MATERIAL:
        _assignMaterialColors(links, link_names, base_link, registry)
    elif color_choice == COLOR_MODE_RAINBOW:
        _assignRainbowColors(links, joints, registry)
    else:
        _assignSingleColor(links, color_choice, registry)

    seen, seen_names = [], set()
    for lnk in links:
        if lnk.material and lnk.material not in seen_names:
            seen_names.add(lnk.material)
            seen.append(MaterialData(lnk.material, registry[lnk.material]))
    return seen


def _assignMaterialColors(links, link_names, base_link, registry):
    occ_map = {'base_link': base_link}
    occ_map.update({name: occ for name, occ in link_names.items() if occ is not base_link})

    for lnk in links:
        occ = occ_map.get(lnk.naming.link)
        if occ is None:
            continue
        name, rgba = _dominantMaterial(occ)
        if name is not None:
            lnk.material = name
            registry[name] = rgba


def _assignRainbowColors(links, joints, registry):
    n = len(_COLORS)
    depth_map = {'base_link': 0}
    for jnt in joints:
        depth_map[jnt.child_link] = depth_map.get(jnt.parent_link, 0) + 1

    for lnk in links:
        depth = depth_map.get(lnk.naming.link, 0)
        color_name, rgba = _COLORS[depth % n]
        lnk.material = color_name
        registry[color_name] = rgba


def _assignSingleColor(links, color_name, registry):
    rgba = next((r for n, r in _COLORS if n == color_name), None)
    if rgba is None:
        return
    registry[color_name] = rgba
    for lnk in links:
        lnk.material = color_name


def _dominantMaterial(occ):
    mat_masses = {}
    mat_colors = {}

    bodies = list(occ.component.bRepBodies)
    for sub in occ.component.allOccurrences:
        bodies.extend(sub.component.bRepBodies)

    for body in bodies:
        mat = body.material
        if mat is None:
            continue
        name = mat.name
        try:
            mass = body.physicalProperties.mass
        except Exception:
            mass = 0.0
        mat_masses[name] = mat_masses.get(name, 0.0) + mass
        if name not in mat_colors:
            rgba = _getMaterialColor(mat)
            if rgba is not None:
                mat_colors[name] = rgba

    eligible = {n: m for n, m in mat_masses.items() if n in mat_colors}
    if not eligible:
        return None, None

    max_mass = max(eligible.values())
    winner = min(n for n, m in eligible.items() if m == max_mass)
    return winner, mat_colors[winner]


def _getMaterialColor(material):
    try:
        props = material.appearance.appearanceProperties
        for i in range(props.count):
            prop = props.item(i)
            if prop.objectType == adsk.core.AppearanceColorProperty.classType():
                c = prop.value
                return (c.red / 255.0, c.green / 255.0, c.blue / 255.0, 1.0)
    except Exception:
        pass
    return None
