import adsk.core
import adsk.fusion
import traceback

_CMD_ID = 'urdFusion_linkSelection'
_EXPORT_MODE_INPUT_ID = 'exportMode'
_SELECTION_INPUT_ID = 'selection'
_BASE_LINK_INPUT_ID = 'baseLink'
_EXPORT_STLS_INPUT_ID = 'exportStls'
_BASE_LINK_PLACEHOLDER = '<select one>'
_MODE_ALL = 'All Top Level Components'
_MODE_CUSTOM = 'Custom'
_handlers = []


def _getTopLevelOccurrences():
    design = adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)
    return [occ for occ in design.rootComponent.occurrences if occ.isVisible]


def _rebuildBaseLinkDropdown(base_link_input, occurrences):
    base_link_input.listItems.clear()
    base_link_input.listItems.add(_BASE_LINK_PLACEHOLDER, True, '')
    for occ in occurrences:
        base_link_input.listItems.add(occ.name, False, '')


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, on_complete):
        super().__init__()
        self._on_complete = on_complete

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            mode_input = inputs.itemById(_EXPORT_MODE_INPUT_ID)
            sel_input = inputs.itemById(_SELECTION_INPUT_ID)
            base_link_input = inputs.itemById(_BASE_LINK_INPUT_ID)
            export_stls_input = inputs.itemById(_EXPORT_STLS_INPUT_ID)

            if mode_input.selectedItem.name == _MODE_ALL:
                components = _getTopLevelOccurrences()
            else:
                components = [sel_input.selection(i).entity for i in range(sel_input.selectionCount)]

            base_link = None
            selected = base_link_input.selectedItem
            if selected and selected.index > 0:  # index 0 is the placeholder
                comp_idx = selected.index - 1
                if 0 <= comp_idx < len(components):
                    base_link = components[comp_idx]

            self._on_complete(components, base_link, export_stls_input.value)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            mode_input = inputs.itemById(_EXPORT_MODE_INPUT_ID)
            sel_input = inputs.itemById(_SELECTION_INPUT_ID)
            base_link_input = inputs.itemById(_BASE_LINK_INPUT_ID)

            if args.input.id == _EXPORT_MODE_INPUT_ID:
                if mode_input.selectedItem.name == _MODE_ALL:
                    sel_input.isVisible = False
                    sel_input.setSelectionLimits(0, 0)
                    _rebuildBaseLinkDropdown(base_link_input, _getTopLevelOccurrences())
                else:
                    sel_input.isVisible = True
                    sel_input.setSelectionLimits(1, 0)
                    occs = [sel_input.selection(i).entity for i in range(sel_input.selectionCount)]
                    _rebuildBaseLinkDropdown(base_link_input, occs)

            elif args.input.id == _SELECTION_INPUT_ID:
                occs = [sel_input.selection(i).entity for i in range(sel_input.selectionCount)]
                _rebuildBaseLinkDropdown(base_link_input, occs)

        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


class _ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            mode_input = inputs.itemById(_EXPORT_MODE_INPUT_ID)
            sel_input = inputs.itemById(_SELECTION_INPUT_ID)
            base_link_input = inputs.itemById(_BASE_LINK_INPUT_ID)

            if mode_input.selectedItem.name == _MODE_ALL:
                has_links = len(_getTopLevelOccurrences()) > 0
            else:
                has_links = sel_input.selectionCount > 0

            selected = base_link_input.selectedItem
            has_base_link = selected is not None and selected.index > 0

            args.areInputsValid = has_links and has_base_link
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


class _DestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        _handlers.clear()


class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, on_complete):
        super().__init__()
        self._on_complete = on_complete

    def notify(self, args):
        try:
            cmd = args.command

            mode_input = cmd.commandInputs.addDropDownCommandInput(
                _EXPORT_MODE_INPUT_ID, 'Export', adsk.core.DropDownStyles.TextListDropDownStyle
            )
            mode_input.listItems.add(_MODE_ALL, True)
            mode_input.listItems.add(_MODE_CUSTOM, False)

            sel_input = cmd.commandInputs.addSelectionInput(
                _SELECTION_INPUT_ID, 'Links', 'Select components to export as URDF links'
            )
            sel_input.addSelectionFilter('Occurrences')
            sel_input.setSelectionLimits(0, 0)  # no minimum while hidden in "All" mode
            sel_input.isVisible = False

            base_link_input = cmd.commandInputs.addDropDownCommandInput(
                _BASE_LINK_INPUT_ID, 'Base Link', adsk.core.DropDownStyles.TextListDropDownStyle
            )
            _rebuildBaseLinkDropdown(base_link_input, _getTopLevelOccurrences())

            cmd.commandInputs.addBoolValueInput(_EXPORT_STLS_INPUT_ID, 'Export STLs', True, '', False)

            on_execute = _ExecuteHandler(self._on_complete)
            cmd.execute.add(on_execute)
            _handlers.append(on_execute)

            on_input_changed = _InputChangedHandler()
            cmd.inputChanged.add(on_input_changed)
            _handlers.append(on_input_changed)

            on_validate = _ValidateInputsHandler()
            cmd.validateInputs.add(on_validate)
            _handlers.append(on_validate)

            on_destroy = _DestroyHandler()
            cmd.destroy.add(on_destroy)
            _handlers.append(on_destroy)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


def show(ui, on_complete):
    cmd_def = ui.commandDefinitions.itemById(_CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()

    cmd_def = ui.commandDefinitions.addButtonDefinition(
        _CMD_ID, 'Export URDF', 'Select components as URDF links'
    )
    on_created = _CreatedHandler(on_complete)
    cmd_def.commandCreated.add(on_created)
    _handlers.append(on_created)

    cmd_def.execute()
