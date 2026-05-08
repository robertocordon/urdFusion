import csv
import os
import shutil
import xml.etree.ElementTree as ET
import adsk.core
import adsk.fusion
import traceback

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
]


def selectExportFolder(ui):
    try:
        dialog = ui.createFolderDialog()
        dialog.title = 'Select Export Folder'
        if dialog.showDialog() != adsk.core.DialogResults.DialogOK:
            return None
        return dialog.folder
    except Exception:
        ui.messageBox(traceback.format_exc())
        return None


def exportCsv(ui, links, joints, folder, robot_name):
    try:
        path = os.path.join(folder, robot_name + '.csv')

        rows = [_LINK_HEADER]
        for lnk in links:
            rows.append([
                lnk.naming.component, lnk.naming.link,
                lnk.origin.x, lnk.origin.y, lnk.origin.z,
                lnk.rotation.r, lnk.rotation.p, lnk.rotation.y,
                lnk.mass,
                lnk.center_of_mass.x, lnk.center_of_mass.y, lnk.center_of_mass.z,
                lnk.inertia.xx, lnk.inertia.xy, lnk.inertia.xz,
                lnk.inertia.yy, lnk.inertia.yz, lnk.inertia.zz,
                lnk.collision_mode or 'none', lnk.material or '',
            ])

        rows.append([])
        rows.append(_JOINT_HEADER)
        for jnt in joints:
            ax = jnt.axis
            xyz, rpy = jnt.origin_xyz, jnt.origin_rpy
            rows.append([
                jnt.name, jnt.urdf_type, jnt.parent_link, jnt.child_link,
                ax[0] if ax else '-', ax[1] if ax else '-', ax[2] if ax else '-',
                xyz[0], xyz[1], xyz[2],
                rpy[0], rpy[1], rpy[2],
                jnt.lower if jnt.lower is not None else '-',
                jnt.upper if jnt.upper is not None else '-',
            ])

        with open(path, 'w', newline='') as f:
            csv.writer(f).writerows(rows)

        return True
    except Exception:
        ui.messageBox(traceback.format_exc())
        return False


def exportStls(ui, links, link_names, base_link, folder):
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

            _exportLinkStl(export_mgr, occ, link_name, stl_folder)
            if _hasHiddenBodies(occ):
                links_with_hidden.append(link_name)

            if col_body:
                if col_mode == 'custom' and col_folder:
                    col_body.isVisible = True
                    _exportBodyStl(export_mgr, col_body, link_name, col_folder)
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


def exportUrdf(ui, links, joints, child_visual_origins, materials, folder, robot_name):
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
                          xyz=f'{c.x} {c.y} {c.z}',
                          rpy='0 0 0')
            ET.SubElement(inertial, 'mass', value=str(lnk.mass))
            i = lnk.inertia
            ET.SubElement(inertial, 'inertia',
                          ixx=str(i.xx), ixy=str(i.xy), ixz=str(i.xz),
                          iyy=str(i.yy), iyz=str(i.yz), izz=str(i.zz))

            mesh_path = 'STL/' + lnk.naming.link + '.stl'
            vis_xyz, vis_rpy = child_visual_origins.get(
                lnk.naming.link, ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
            )
            vis_attrib = {
                'xyz': f'{vis_xyz[0]} {vis_xyz[1]} {vis_xyz[2]}',
                'rpy': f'{vis_rpy[0]} {vis_rpy[1]} {vis_rpy[2]}',
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
                          xyz=f'{xyz[0]} {xyz[1]} {xyz[2]}',
                          rpy=f'{rpy[0]} {rpy[1]} {rpy[2]}')
            if jnt.axis is not None:
                ax = jnt.axis
                ET.SubElement(jel, 'axis', xyz=f'{ax[0]} {ax[1]} {ax[2]}')
            if jnt.effort is not None:
                ET.SubElement(jel, 'limit',
                              lower=str(jnt.lower) if jnt.lower is not None else '0',
                              upper=str(jnt.upper) if jnt.upper is not None else '0',
                              effort=str(jnt.effort),
                              velocity=str(jnt.velocity))

        tree = ET.ElementTree(robot)
        ET.indent(tree, space='  ')
        path = os.path.join(folder, robot_name + '.urdf')
        with open(path, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)

        return True
    except Exception:
        ui.messageBox(traceback.format_exc())
        return False


def _rgba(rgba):
    return ' '.join(f'{v:.4f}' for v in rgba)


def _hasHiddenBodies(occ):
    for body in occ.component.bRepBodies:
        if body.name not in _COLLISION_BODY_NAMES and not body.isVisible:
            return True
    for sub in occ.component.allOccurrences:
        for body in sub.component.bRepBodies:
            if not body.isVisible:
                return True
    return False


def _exportLinkStl(export_mgr, occ, link_name, folder):
    filename = os.path.join(folder, link_name + '.stl')
    options = export_mgr.createSTLExportOptions(occ.component, filename)
    options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    options.isBinaryFormat = True
    options.sendToPrintUtility = False
    options.unitType = adsk.fusion.DistanceUnits.MeterDistanceUnits
    export_mgr.execute(options)


def _exportBodyStl(export_mgr, body, link_name, folder):
    filename = os.path.join(folder, link_name + '.stl')
    options = export_mgr.createSTLExportOptions(body, filename)
    options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    options.isBinaryFormat = True
    options.sendToPrintUtility = False
    options.unitType = adsk.fusion.DistanceUnits.MeterDistanceUnits
    export_mgr.execute(options)
