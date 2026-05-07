from modules import linkSelectionDialog, linkSelection, urdfExport


def execute(ui):
    def _linkSelectionComplete(components, base_link):
        if not linkSelection.checkAllBodiesSelected(components):
            return

        link_names = linkSelection.getUniqueLinkNames(components)
        if not link_names:
            return

        folder = urdfExport.selectExportFolder(ui)
        if not folder:
            return

        urdfExport.exportCsv(ui, link_names, base_link, folder)
        urdfExport.exportStls(ui, link_names, base_link, folder)

    linkSelectionDialog.show(ui, _linkSelectionComplete)
