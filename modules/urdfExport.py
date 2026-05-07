import csv
import os
import shutil
import xml.etree.ElementTree as ET
import adsk.core
import adsk.fusion
import traceback

_HEADER = [
    'Component Name', 'Link Name',
    'Offset X', 'Offset Y', 'Offset Z',
    'Roll', 'Pitch', 'Yaw',
    'Mass',
    'CoM X', 'CoM Y', 'CoM Z',
    'Ixx', 'Ixy', 'Ixz', 'Iyy', 'Iyz', 'Izz',
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


def exportCsv(ui, links, folder, robot_name):
    try:
        path = os.path.join(folder, robot_name + '.csv')

        rows = [_HEADER]
        for lnk in links:
            rows.append([
                lnk.naming.component, lnk.naming.link,
                lnk.origin.x, lnk.origin.y, lnk.origin.z,
                lnk.rotation.r, lnk.rotation.p, lnk.rotation.y,
                lnk.mass,
                lnk.center_of_mass.x, lnk.center_of_mass.y, lnk.center_of_mass.z,
                lnk.inertia.xx, lnk.inertia.xy, lnk.inertia.xz,
                lnk.inertia.yy, lnk.inertia.yz, lnk.inertia.zz,
            ])

        with open(path, 'w', newline='') as f:
            csv.writer(f).writerows(rows)

    except Exception:
        ui.messageBox(traceback.format_exc())


def exportStls(ui, link_names, base_link, folder):
    try:
        stl_folder = os.path.join(folder, 'STL')
        shutil.rmtree(stl_folder, ignore_errors=True)
        os.makedirs(stl_folder)

        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        export_mgr = design.exportManager

        links_with_hidden = []

        _exportLinkStl(export_mgr, base_link, 'base_link', stl_folder)
        if _hasHiddenBodies(base_link):
            links_with_hidden.append('base_link')

        for name, occ in sorted(
            ((n, o) for n, o in link_names.items() if o is not base_link),
            key=lambda item: item[0]
        ):
            _exportLinkStl(export_mgr, occ, name, stl_folder)
            if _hasHiddenBodies(occ):
                links_with_hidden.append(name)

        if links_with_hidden:
            ui.messageBox(
                'The following links contained bodies that were hidden. '
                'They will not be visible in the STLs, but their mass will be counted in the URDF.\n\n' +
                '\n'.join(links_with_hidden),
                'Hidden Bodies Warning'
            )

    except Exception:
        ui.messageBox(traceback.format_exc())


def exportUrdf(ui, links, joints, child_visual_origins, folder, robot_name):
    try:
        robot = ET.Element('robot', name=robot_name)

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

            for tag in ('visual', 'collision'):
                el = ET.SubElement(link_el, tag)
                ET.SubElement(el, 'origin', **vis_attrib)
                geometry = ET.SubElement(el, 'geometry')
                ET.SubElement(geometry, 'mesh', filename=mesh_path)

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

    except Exception:
        ui.messageBox(traceback.format_exc())


def _hasHiddenBodies(occ):
    for body in occ.component.bRepBodies:
        if not body.isVisible:
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
