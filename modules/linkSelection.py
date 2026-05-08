import re
import adsk.core
import adsk.fusion
import traceback

from modules import utils


def getRootLinkName() -> str:
    try:
        design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
        name = re.sub(r'\s+v\d+$', '', design.rootComponent.name)
        return utils.sanitizeName(name)
    except Exception:
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())
        return None


def checkAllBodiesSelected(components: list) -> bool:
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


def getUniqueLinkNames(components: list) -> dict:
    try:
        ui = adsk.core.Application.get().userInterface

        parsed = []
        for occ in components:
            parts = occ.name.split(':', 1)
            base = utils.sanitizeName(parts[0])
            suffix = parts[1] if len(parts) > 1 else ''
            if not base:
                ui.messageBox(
                    'Component "' + occ.name + '" produces an empty URDF link name after '
                    'sanitization. Rename it so it contains at least one letter.',
                    'Invalid Component Name'
                )
                return None
            parsed.append((base, suffix, occ))

        base_counts = {}
        for base, _, _ in parsed:
            base_counts[base] = base_counts.get(base, 0) + 1

        result = {}
        for base, suffix, occ in parsed:
            if base_counts[base] > 1 and suffix:
                name = base + '_' + suffix
            else:
                name = base

            if name in result:
                ui.messageBox(
                    'Cannot generate unique URDF link names. The name "' + name +
                    '" maps to more than one component. Please rename the components '
                    'so each one resolves to a unique link name.',
                    'Duplicate Link Names'
                )
                return None

            result[name] = occ

        return result

    except Exception:
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())
        return None


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
