import adsk.core
import traceback

_CMD_ID = 'urdFusion_linkSelection'
_SELECTION_INPUT_ID = 'selection'
_BASE_LINK_INPUT_ID = 'baseLink'
_BASE_LINK_PLACEHOLDER = '<select one>'
_handlers = []


def _rebuildBaseLinkDropdown(sel_input, base_link_input):
    base_link_input.listItems.clear()
    base_link_input.listItems.add(_BASE_LINK_PLACEHOLDER, True, '')
    for i in range(sel_input.selectionCount):
        comp = sel_input.selection(i).entity
        base_link_input.listItems.add(comp.name, False, '')


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, on_complete):
        super().__init__()
        self._on_complete = on_complete

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            sel_input = inputs.itemById(_SELECTION_INPUT_ID)
            components = [sel_input.selection(i).entity for i in range(sel_input.selectionCount)]

            base_link_input = inputs.itemById(_BASE_LINK_INPUT_ID)
            base_link = None
            selected = base_link_input.selectedItem
            if selected and selected.index > 0:  # index 0 is the placeholder
                comp_idx = selected.index - 1
                if 0 <= comp_idx < len(components):
                    base_link = components[comp_idx]

            self._on_complete(components, base_link)
        except Exception:
            adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            if args.input.id != _SELECTION_INPUT_ID:
                return

            inputs = args.firingEvent.sender.commandInputs
            sel_input = inputs.itemById(_SELECTION_INPUT_ID)
            base_link_input = inputs.itemById(_BASE_LINK_INPUT_ID)
            _rebuildBaseLinkDropdown(sel_input, base_link_input)
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

            sel_input = cmd.commandInputs.addSelectionInput(
                _SELECTION_INPUT_ID, 'Links', 'Select components to export as URDF links'
            )
            sel_input.addSelectionFilter('Occurrences')
            sel_input.setSelectionLimits(1, 0)  # min 1, max unlimited

            base_link_input = cmd.commandInputs.addDropDownCommandInput(
                _BASE_LINK_INPUT_ID, 'Base Link', adsk.core.DropDownStyles.TextListDropDownStyle
            )
            base_link_input.listItems.add(_BASE_LINK_PLACEHOLDER, True, '')

            on_execute = _ExecuteHandler(self._on_complete)
            cmd.execute.add(on_execute)
            _handlers.append(on_execute)

            on_input_changed = _InputChangedHandler()
            cmd.inputChanged.add(on_input_changed)
            _handlers.append(on_input_changed)

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
        _CMD_ID, 'Select Links', 'Select components as URDF links'
    )
    on_created = _CreatedHandler(on_complete)
    cmd_def.commandCreated.add(on_created)
    _handlers.append(on_created)

    cmd_def.execute()
