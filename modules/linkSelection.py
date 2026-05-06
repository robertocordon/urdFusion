import adsk.core
import adsk.fusion
import traceback


def checkAllBodiesSelected(components):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)

        selected_tokens = {occ.entityToken for occ in components}
        uncovered = _findUncoveredBodies(design.rootComponent, selected_tokens)

        if not uncovered:
            return True

        body_list = '\n'.join(path for _, path in uncovered)
        ui.messageBox(
            'The following visible bodies are not part of your selection:\n\n' +
            body_list +
            '\n\nExpand your selection to include the components containing '
            'these bodies, or hide them in the browser before continuing.',
            'Incomplete Selection'
        )
        return False

    except Exception:
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())
        return False


def _findUncoveredBodies(root, selected_tokens):
    uncovered = []

    for body in root.bRepBodies:
        if body.isVisible:
            uncovered.append((body, 'root -> ' + body.name))

    for occ in root.allOccurrences:
        if not occ.isVisible:
            continue
        if occ.entityToken in selected_tokens:
            continue
        if _hasSelectedAncestor(occ, selected_tokens):
            continue
        for body in occ.component.bRepBodies:
            if body.isVisible:
                uncovered.append((body, _buildPath(occ) + ' -> ' + body.name))

    return uncovered


def _hasSelectedAncestor(occ, selected_tokens):
    parent = occ.assemblyContext
    while parent is not None:
        if parent.entityToken in selected_tokens:
            return True
        parent = parent.assemblyContext
    return False


def _buildPath(occ):
    parts = []
    current = occ
    while current is not None:
        parts.append(current.name)
        current = current.assemblyContext
    parts.reverse()
    return 'root -> ' + ' -> '.join(parts)
