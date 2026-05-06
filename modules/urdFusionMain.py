from modules import linkSelectionDialog, linkSelection


def execute(ui):
    def _linkSelectionComplete(components, base_link):
        if not linkSelection.checkAllBodiesSelected(components):
            return

        link_names = linkSelection.getUniqueLinkNames(components)
        if not link_names:
            return

        base_name = base_link.name if base_link else '(none)'
        pairs = '\n'.join(name + '  (' + occ.name + ')' for name, occ in link_names.items())
        ui.messageBox(
            'Base link: ' + base_name + '\n\nURDF links:\n' + pairs
        )

    linkSelectionDialog.show(ui, _linkSelectionComplete)
