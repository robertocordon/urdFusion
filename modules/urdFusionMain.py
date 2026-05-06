from modules import linkSelectionDialog, linkSelection


def execute(ui):
    def _linkSelectionComplete(components, base_link):
        if not linkSelection.checkAllBodiesSelected(components):
            return

        names = [c.name for c in components]
        base_name = base_link.name if base_link else '(none)'
        ui.messageBox(
            'Base link: ' + base_name + '\n\nLinks:\n' + '\n'.join(names)
        )

    linkSelectionDialog.show(ui, _linkSelectionComplete)
