import csv
import os
import adsk.core
import adsk.fusion
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


def exportStls(ui, link_names, base_link):
    try:
        folder_dialog = ui.createFolderDialog()
        folder_dialog.title = 'Select STL Export Folder'
        if folder_dialog.showDialog() != adsk.core.DialogResults.DialogOK:
            return

        folder = folder_dialog.folder
        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        export_mgr = design.exportManager

        _exportLinkStl(export_mgr, base_link, 'base_link', folder)
        for name, occ in sorted(
            ((n, o) for n, o in link_names.items() if o is not base_link),
            key=lambda item: item[0]
        ):
            _exportLinkStl(export_mgr, occ, name, folder)

        ui.messageBox('STLs exported to:\n' + folder, 'Export Complete')

    except Exception:
        ui.messageBox(traceback.format_exc())


def _exportLinkStl(export_mgr, occ, link_name, folder):
    filename = os.path.join(folder, link_name + '.stl')
    options = export_mgr.createSTLExportOptions(occ.component, filename)
    options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    options.isBinaryFormat = True
    options.sendToPrintUtility = False
    options.unitType = adsk.fusion.DistanceUnits.MeterDistanceUnits
    export_mgr.execute(options)
