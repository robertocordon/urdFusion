from modules import linkSelectionDialog, linkSelection


def execute(ui):
    def _linkSelectionComplete(components):
        if not linkSelection.checkAllBodiesSelected(components):
            return

        names = [c.name for c in components]
        ui.messageBox('Selected links:\n' + '\n'.join(names))

    linkSelectionDialog.show(ui, _linkSelectionComplete)
