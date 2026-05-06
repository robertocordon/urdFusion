from modules import linkSelectionDialog


def execute(ui):
    def _linkSelectionComplete(components):
        names = [c.name for c in components]
        ui.messageBox('Selected links:\n' + '\n'.join(names))

    linkSelectionDialog.show(ui, _linkSelectionComplete)
