from modules import linkSelectionDialog, linkSelection, urdfExport


def execute(ui):
    def _linkSelectionComplete(components, base_link):
        if not linkSelection.checkAllBodiesSelected(components):
            return

        link_names = linkSelection.getUniqueLinkNames(components)
        if not link_names:
            return

        root_name = linkSelection.getRootLinkName()
        if not root_name:
            return

        folder = urdfExport.selectExportFolder(ui)
        if not folder:
            return

        urdfExport.exportCsv(ui, link_names, base_link, folder, root_name)
        urdfExport.exportStls(ui, link_names, base_link, folder)
        urdfExport.exportUrdf(ui, link_names, base_link, folder, root_name)
        ui.messageBox('URDF export complete')

    linkSelectionDialog.show(ui, _linkSelectionComplete)
