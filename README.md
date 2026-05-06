# urdFusion
Export URDF files from Fusion360

## Usage
* Create a symlink to the repo in `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
* In Fusion, go to Utilities -> Add-Ins -> Scripts and Add-Ins
* Look for `urdFusion` and toggle on. Also check `Run on Startup`
* Under `Add-Ins` a new button for `urdFusion` is present. Press it to run.

## Development
* When the `urdFusion` button is pressed, all modules are reloaded. So any changes to modules will automatically be picked up.
* Changes to `urdFusion.py` will require the toggle (see [Usage](#usage)) to be turned off and back on. 
  * The only changes there should be when a new module is added.
  * Add the import, and then update `reloadModules`. The order matters, deeper reloads go in first.

## Roadmap
* Allow choosing of base link
* Allow choosing of other links
* Check if all visible bodies are part of selection - warn if not
* Check if all bodies (or parent components) have a material assigned - warn if not
* Generate CSV file with all links and their mass, center of mass and inertial vectors. 
* Export STLs
* Generate URDF with all links
* Add materials to URDF (ie colors)
* Allow user to select colors for links
* Export joints