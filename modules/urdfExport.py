import csv
from dataclasses import dataclass
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


@dataclass
class _Naming:
    component: str
    link: str


@dataclass
class _Point3:
    x: float
    y: float
    z: float


@dataclass
class _Inertia:
    xx: float
    xy: float
    xz: float
    yy: float
    yz: float
    zz: float


@dataclass
class _URDFLink:
    naming: _Naming
    mass: float
    origin: _Point3
    center_of_mass: _Point3
    inertia: _Inertia


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

        links = _collectURDFData(link_names, base_link)

        rows = [_HEADER]
        for lnk in links:
            rows.append([
                lnk.naming.component, lnk.naming.link,
                lnk.origin.x, lnk.origin.y, lnk.origin.z,
                lnk.mass,
                lnk.center_of_mass.x, lnk.center_of_mass.y, lnk.center_of_mass.z,
                lnk.inertia.xx, lnk.inertia.xy, lnk.inertia.xz,
                lnk.inertia.yy, lnk.inertia.yz, lnk.inertia.zz,
            ])

        with open(path, 'w', newline='') as f:
            csv.writer(f).writerows(rows)

        ui.messageBox('CSV exported to:\n' + path, 'Export Complete')

    except Exception:
        ui.messageBox(traceback.format_exc())


def _collectURDFData(link_names, base_link):
    base = _buildLink(base_link, 'base_link')
    rest = sorted(
        [_buildLink(occ, name) for name, occ in link_names.items() if occ is not base_link],
        key=lambda lnk: lnk.naming.link
    )
    return [base] + rest


def _buildLink(occ, link_name):
    tf = occ.transform.translation
    origin = _Point3(tf.x * _CM_TO_M, tf.y * _CM_TO_M, tf.z * _CM_TO_M)

    props = occ.component.physicalProperties
    mass = props.mass

    com = props.centerOfMass
    center_of_mass = _Point3(com.x * _CM_TO_M, com.y * _CM_TO_M, com.z * _CM_TO_M)

    (_, xx, yy, zz, xy, yz, xz) = props.getXYZMomentsOfInertia()
    ixx, iyy, izz, ixy, iyz, ixz = [v * _KGCM2_TO_KGM2 for v in [xx, yy, zz, xy, yz, xz]]

    x, y, z = center_of_mass.x, center_of_mass.y, center_of_mass.z
    offsets = [y**2 + z**2, x**2 + z**2, x**2 + y**2, -x*y, -y*z, -x*z]
    ixx, iyy, izz, ixy, iyz, ixz = [
        i - mass * d for i, d in zip([ixx, iyy, izz, ixy, iyz, ixz], offsets)
    ]
    inertia = _Inertia(ixx, ixy, ixz, iyy, iyz, izz)

    return _URDFLink(
        _Naming(occ.name, link_name),
        mass,
        origin,
        center_of_mass,
        inertia,
    )
