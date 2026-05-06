import os
import sys
import importlib
import traceback
import adsk.core

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import linkSelectionDialog, linkSelection, urdfExport, urdFusionMain

ui = adsk.core.Application.get().userInterface

_CMD_ID = 'urdFusion_export'
_handlers = []


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            reloadModules()
            urdFusionMain.execute(ui)
        except Exception:
            ui.messageBox(traceback.format_exc())


class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            on_execute = _ExecuteHandler()
            args.command.execute.add(on_execute)
            _handlers.append(on_execute)
        except Exception:
            ui.messageBox(traceback.format_exc())


def _register():
    _unregister()

    cmd_def = ui.commandDefinitions.addButtonDefinition(_CMD_ID, 'urdFusion', 'Export model to URDF')
    on_created = _CreatedHandler()
    cmd_def.commandCreated.add(on_created)
    _handlers.append(on_created)

    panel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    panel.controls.addCommand(cmd_def)


def _unregister():
    _handlers.clear()

    panel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
    control = panel.controls.itemById(_CMD_ID)
    if control:
        control.deleteMe()

    cmd_def = ui.commandDefinitions.itemById(_CMD_ID)
    if cmd_def:
        cmd_def.deleteMe()


def run(context):
    try:
        _register()
    except Exception:
        ui.messageBox(traceback.format_exc())


def stop(context):
    try:
        _unregister()
    except Exception:
        ui.messageBox(traceback.format_exc())

#avoids stale modules during development
def reloadModules():
    importlib.reload(linkSelectionDialog)
    importlib.reload(linkSelection)
    importlib.reload(urdfExport)
    importlib.reload(urdFusionMain)

