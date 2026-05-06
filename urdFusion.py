import os
import sys
import traceback
import adsk.core

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import hello_world


def run(context):
    try:

        ui = adsk.core.Application.get().userInterface
        hello_world.execute(ui)
    except Exception:
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


def stop(context):
    pass
