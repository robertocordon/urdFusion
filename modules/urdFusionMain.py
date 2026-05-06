from modules import linkSelectionDialog


def execute(ui):
    def _linkSelectionComplete(components):
        pass  # validator call goes here later

    linkSelectionDialog.show(ui, _linkSelectionComplete)
