import adsk.core
import traceback

_CMD_ID = 'urdFusion_linkSelection'
_handlers = []


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, on_complete):
        super().__init__()
        self._on_complete = on_complete

    def notify(self, args):
        try:
            inputs = args.firingEvent.sender.commandInputs
            sel_input = inputs.itemById('selection')
            components = [sel_input.selection(i).entity for i in range(sel_input.selectionCount)]
            self._on_complete(components)
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
                'selection', 'Links', 'Select components to export as URDF links'
            )
            sel_input.addSelectionFilter('Occurrences')
            sel_input.setSelectionLimits(1, 0)  # min 1, max unlimited

            on_execute = _ExecuteHandler(self._on_complete)
            cmd.execute.add(on_execute)
            _handlers.append(on_execute)

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
