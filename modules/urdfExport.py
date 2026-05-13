import csv
import os
import shutil
import xml.etree.ElementTree as ET
import adsk.core
import adsk.fusion
import traceback

from modules.urdfJoint import VisualOrigin

_ZERO_ORIGIN = VisualOrigin((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

_COLLISION_BODY_NAMES = frozenset({'urdfCollision', 'urdfSameCollision'})

_LINK_HEADER = [
    'Component Name', 'Link Name',
    'Offset X', 'Offset Y', 'Offset Z',
    'Roll', 'Pitch', 'Yaw',
    'Mass',
    'CoM X', 'CoM Y', 'CoM Z',
    'Ixx', 'Ixy', 'Ixz', 'Iyy', 'Iyz', 'Izz',
    'Collision Mesh', 'Material',
]

_JOINT_HEADER = [
    'Joint Name', 'Joint Type', 'Parent', 'Child',
    'Axis X', 'Axis Y', 'Axis Z',
    'Origin X', 'Origin Y', 'Origin Z',
    'Origin Roll', 'Origin Pitch', 'Origin Yaw',
    'Lower Limit', 'Upper Limit',
    'Damping', 'Friction', 'Effort', 'Velocity',
]



def exportCsv(ui, links: list, joints: list, folder: str, robot_name: str) -> bool:
    try:
        path = os.path.join(folder, robot_name + '.csv')

        def _r(v): return round(v, 6)
        def _ri(v): return round(v, 10)  # inertia: kill noise, keep sig figs for spreadsheet

        rows = [_LINK_HEADER]
        for lnk in links:
            rows.append([
                lnk.naming.component, lnk.naming.link,
                _r(lnk.origin.x), _r(lnk.origin.y), _r(lnk.origin.z),
                _r(lnk.rotation.r), _r(lnk.rotation.p), _r(lnk.rotation.y),
                _r(lnk.mass),
                _r(lnk.center_of_mass.x), _r(lnk.center_of_mass.y), _r(lnk.center_of_mass.z),
                _ri(lnk.inertia.xx), _ri(lnk.inertia.xy), _ri(lnk.inertia.xz),
                _ri(lnk.inertia.yy), _ri(lnk.inertia.yz), _ri(lnk.inertia.zz),
                lnk.collision_mode or 'none', lnk.material or '',
            ])

        rows.append([])
        rows.append(_JOINT_HEADER)
        for jnt in joints:
            ax = jnt.axis
            xyz, rpy = jnt.origin_xyz, jnt.origin_rpy
            rows.append([
                jnt.name, jnt.urdf_type, jnt.parent_link, jnt.child_link,
                _r(ax[0]) if ax else '-', _r(ax[1]) if ax else '-', _r(ax[2]) if ax else '-',
                _r(xyz[0]), _r(xyz[1]), _r(xyz[2]),
                _r(rpy[0]), _r(rpy[1]), _r(rpy[2]),
                _r(jnt.lower) if jnt.lower is not None else '-',
                _r(jnt.upper) if jnt.upper is not None else '-',
                _fmtParam(jnt.params.damping, None),
                _fmtParam(jnt.params.friction, None),
                jnt.params.effort if jnt.urdf_type != 'fixed' else '-',
                jnt.params.velocity if jnt.urdf_type != 'fixed' else '-',
            ])

        with open(path, 'w', newline='') as f:
            csv.writer(f).writerows(rows)

        return True
    except Exception:
        ui.messageBox(traceback.format_exc())
        return False


def exportStls(ui, links: list, link_names: dict, base_link, folder: str) -> bool:
    try:
        stl_folder = os.path.join(folder, 'STL')
        shutil.rmtree(stl_folder, ignore_errors=True)
        os.makedirs(stl_folder)

        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        export_mgr = design.exportManager

        link_map = {lnk.naming.link: lnk for lnk in links}
        pairs = [('base_link', base_link)] + sorted(
            ((n, o) for n, o in link_names.items() if o is not base_link),
            key=lambda item: item[0]
        )

        needs_col_folder = any(
            link_map.get(name) and link_map[name].collision_mode == 'custom'
            for name, _ in pairs
        )
        col_folder = None
        if needs_col_folder:
            col_folder = os.path.join(stl_folder, 'collision')
            os.makedirs(col_folder)

        links_with_hidden = []
        col_mass_warnings = []

        for link_name, occ in pairs:
            lnk = link_map.get(link_name)
            col_mode = lnk.collision_mode if lnk else None

            col_body = None
            if col_mode in ('custom', 'same'):
                body_name = 'urdfCollision' if col_mode == 'custom' else 'urdfSameCollision'
                col_body = next(
                    (b for b in occ.component.bRepBodies if b.name == body_name), None
                )
                if col_body:
                    try:
                        col_mass = col_body.physicalProperties.mass
                        if col_mass > 1e-6:
                            col_mass_warnings.append(
                                f'{link_name} ({body_name}): {col_mass:.4f} kg'
                            )
                    except Exception:
                        pass

            saved_vis = None
            if col_body:
                saved_vis = col_body.isVisible
                col_body.isVisible = False

            _exportStl(export_mgr, occ.component, link_name, stl_folder)
            if _hasHiddenBodies(occ):
                links_with_hidden.append(link_name)

            if col_body:
                if col_mode == 'custom' and col_folder:
                    col_body.isVisible = True
                    _exportStl(export_mgr, col_body, link_name, col_folder)
                col_body.isVisible = saved_vis

        if links_with_hidden:
            ui.messageBox(
                'The following links contained bodies that were hidden. '
                'They will not be visible in the STLs, but their mass will be counted in the URDF.\n\n' +
                '\n'.join(links_with_hidden),
                'Hidden Bodies Warning'
            )

        if col_mass_warnings:
            ui.messageBox(
                'The following collision bodies have non-zero mass, which will skew '
                'inertial properties. Assign a custom near-zero-density material '
                '(e.g. 0.001 kg/m³) to eliminate their contribution:\n\n' +
                '\n'.join(col_mass_warnings),
                'Collision Body Mass Warning'
            )

        return True
    except Exception:
        ui.messageBox(traceback.format_exc())
        return False


def exportUrdf(ui, links: list, joints: list, child_visual_origins: dict, materials: list, folder: str, robot_name: str) -> bool:
    try:
        robot = ET.Element('robot', name=robot_name)

        for mat in materials:
            mat_el = ET.SubElement(robot, 'material', name=mat.name)
            ET.SubElement(mat_el, 'color', rgba=_rgba(mat.rgba))

        for lnk in links:
            link_el = ET.SubElement(robot, 'link', name=lnk.naming.link)

            inertial = ET.SubElement(link_el, 'inertial')
            c = lnk.center_of_mass
            ET.SubElement(inertial, 'origin',
                          xyz=_fxyz(c.x, c.y, c.z),
                          rpy='0 0 0')
            ET.SubElement(inertial, 'mass', value=_f(lnk.mass))
            i = lnk.inertia
            ET.SubElement(inertial, 'inertia',
                          ixx=_fi(i.xx), ixy=_fi(i.xy), ixz=_fi(i.xz),
                          iyy=_fi(i.yy), iyz=_fi(i.yz), izz=_fi(i.zz))

            mesh_path = 'STL/' + lnk.naming.link + '.stl'
            vis = child_visual_origins.get(lnk.naming.link, _ZERO_ORIGIN)
            vis_attrib = {
                'xyz': _fxyz(*vis.xyz),
                'rpy': _frpy(*vis.rpy),
            }

            vis_el = ET.SubElement(link_el, 'visual')
            ET.SubElement(vis_el, 'origin', **vis_attrib)
            vis_geom = ET.SubElement(vis_el, 'geometry')
            ET.SubElement(vis_geom, 'mesh', filename=mesh_path)
            if lnk.material:
                ET.SubElement(vis_el, 'material', name=lnk.material)

            if lnk.collision_mode in ('same', 'custom'):
                col_path = (mesh_path if lnk.collision_mode == 'same'
                            else 'STL/collision/' + lnk.naming.link + '.stl')
                col_el = ET.SubElement(link_el, 'collision')
                ET.SubElement(col_el, 'origin', **vis_attrib)
                col_geom = ET.SubElement(col_el, 'geometry')
                ET.SubElement(col_geom, 'mesh', filename=col_path)

        for jnt in joints:
            jel = ET.SubElement(robot, 'joint', name=jnt.name, type=jnt.urdf_type)
            ET.SubElement(jel, 'parent', link=jnt.parent_link)
            ET.SubElement(jel, 'child', link=jnt.child_link)
            xyz, rpy = jnt.origin_xyz, jnt.origin_rpy
            ET.SubElement(jel, 'origin',
                          xyz=_fxyz(*xyz),
                          rpy=_frpy(*rpy))
            if jnt.axis is not None:
                ax = jnt.axis
                ET.SubElement(jel, 'axis', xyz=_fxyz(*ax))
            if jnt.urdf_type == 'continuous':
                ET.SubElement(jel, 'limit',
                              effort=_f(jnt.params.effort),
                              velocity=_f(jnt.params.velocity))
            elif jnt.urdf_type in ('revolute', 'prismatic'):
                ET.SubElement(jel, 'limit',
                              lower=_f(jnt.lower) if jnt.lower is not None else '0',
                              upper=_f(jnt.upper) if jnt.upper is not None else '0',
                              effort=_f(jnt.params.effort),
                              velocity=_f(jnt.params.velocity))
            d, f = jnt.params.damping, jnt.params.friction
            if d is not None or f is not None:
                dyn_attribs = {}
                if d is not None:
                    dyn_attribs['damping'] = _f(d)
                if f is not None:
                    dyn_attribs['friction'] = _f(f)
                ET.SubElement(jel, 'dynamics', **dyn_attribs)

        tree = ET.ElementTree(robot)
        ET.indent(tree, space='  ')
        path = os.path.join(folder, robot_name + '.urdf')
        with open(path, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)

        return True
    except Exception:
        ui.messageBox(traceback.format_exc())
        return False


def _f(v: float) -> str:
    """6 decimal places — eliminates near-zero float noise for positions, angles, mass."""
    return str(round(v, 6))


def _fi(v: float) -> str:
    """6 significant figures for inertia; rounds to 10 dp first to kill ~1e-32 noise."""
    return f'{round(v, 10):.6g}'


def _fxyz(a: float, b: float, c: float) -> str:
    return f'{_f(a)} {_f(b)} {_f(c)}'


def _frpy(a: float, b: float, c: float) -> str:
    return f'{_f(a)} {_f(b)} {_f(c)}'


def _fmtParam(user_val, default_val) -> str:
    if user_val is not None:
        return user_val
    if default_val is not None:
        return f'default: {default_val}'
    return '-'


def _rgba(rgba: tuple) -> str:
    return ' '.join(f'{v:.4f}' for v in rgba)


def _hasHiddenBodies(occ) -> bool:
    for body in occ.component.bRepBodies:
        if body.name not in _COLLISION_BODY_NAMES and not body.isVisible:
            return True
    for sub in occ.component.allOccurrences:
        for body in sub.component.bRepBodies:
            if not body.isVisible:
                return True
    return False


def _exportStl(export_mgr, entity, link_name: str, folder: str) -> None:
    filename = os.path.join(folder, link_name + '.stl')
    options = export_mgr.createSTLExportOptions(entity, filename)
    options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    options.isBinaryFormat = True
    options.sendToPrintUtility = False
    options.unitType = adsk.fusion.DistanceUnits.MeterDistanceUnits
    export_mgr.execute(options)
