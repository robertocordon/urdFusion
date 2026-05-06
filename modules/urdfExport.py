import csv
import adsk.core
import traceback

from modules import urdfLink as ul

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

        links = ul.collectLinksData(link_names, base_link)

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
