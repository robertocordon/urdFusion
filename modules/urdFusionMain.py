from modules import linkSelectionDialog, linkSelection, urdfLink, urdfJoint, urdfMaterials, urdfExport


def execute(ui):
    def _linkSelectionComplete(components, base_link, export_stls, color_choice):
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

        links = urdfLink.collectLinksData(link_names, base_link)
        joints, child_visual_origins = urdfJoint.collectJointsData(link_names, base_link)
        materials = urdfMaterials.populateMaterials(links, joints, color_choice, link_names, base_link)

        urdfExport.exportCsv(ui, links, folder, root_name)
        if export_stls:
            urdfExport.exportStls(ui, link_names, base_link, folder)
        urdfExport.exportUrdf(ui, links, joints, child_visual_origins, materials, folder, root_name)
        ui.messageBox('URDF export complete')

    linkSelectionDialog.show(ui, _linkSelectionComplete)
