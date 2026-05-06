import csv
import adsk.core
import traceback

_CM_TO_M = 0.01
_KGCM2_TO_KGM2 = _CM_TO_M ** 2  # kg·cm² → kg·m²

_HEADER = [
    'Component Name', 'Link Name',
    'Offset X', 'Offset Y', 'Offset Z',
    'Mass',
    'CoM X', 'CoM Y', 'CoM Z',
    'Ixx', 'Ixy', 'Ixz', 'Iyy', 'Iyz', 'Izz',
]


def exportCsv(ui, link_names, base_link):
    try:
        dialog = ui.createFileDialog()
        dialog.title = 'Save URDF CSV'
        dialog.filter = 'CSV files (*.csv)'
        dialog.initialFilename = 'urdf_links'
        if dialog.showSave() != adsk.core.DialogResults.DialogOK:
            return

        path = dialog.filename
        if not path.endswith('.csv'):
            path += '.csv'

        rest = {name: occ for name, occ in link_names.items() if occ is not base_link}

        rows = [_HEADER]
        rows.append(_buildRow(base_link, 'base_link'))
        for link_name in sorted(rest):
            rows.append(_buildRow(rest[link_name], link_name))

        with open(path, 'w', newline='') as f:
            csv.writer(f).writerows(rows)

        ui.messageBox('CSV exported to:\n' + path, 'Export Complete')

    except Exception:
        ui.messageBox(traceback.format_exc())


def _buildRow(occ, link_name):
    t = occ.transform.translation  # component origin in world space, cm
    offset_x = t.x * _CM_TO_M
    offset_y = t.y * _CM_TO_M
    offset_z = t.z * _CM_TO_M

    props = occ.component.physicalProperties  # local component space
    mass = props.mass  # kg

    com = props.centerOfMass  # Point3D, cm, relative to component origin
    com_x = com.x * _CM_TO_M
    com_y = com.y * _CM_TO_M
    com_z = com.z * _CM_TO_M

    # Fusion returns (bool, ixx, iyy, izz, ixy, ixz, iyz) in kg·cm²
    (_, ixx, iyy, izz, ixy, ixz, iyz) = props.getXYZMomentsOfInertia()
    ixx *= _KGCM2_TO_KGM2
    ixy *= _KGCM2_TO_KGM2
    ixz *= _KGCM2_TO_KGM2
    iyy *= _KGCM2_TO_KGM2
    iyz *= _KGCM2_TO_KGM2
    izz *= _KGCM2_TO_KGM2

    return [
        occ.name, link_name,
        offset_x, offset_y, offset_z,
        mass,
        com_x, com_y, com_z,
        ixx, ixy, ixz, iyy, iyz, izz,
    ]
