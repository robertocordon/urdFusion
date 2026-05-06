import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import hello_world


def run(context):
    try:
        hello_world.execute()
    except Exception:
        import adsk.core
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc())


def stop(context):
    pass
