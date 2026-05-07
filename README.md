# urdFusion
Export URDF files from Fusion360

## Usage
### Installation
* Create a symlink to the repo in `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` (or just check it out there)
* In Fusion, go to Utilities -> Add-Ins -> Scripts and Add-Ins
* Look for `urdFusion` and toggle on. Also check `Run on Startup`

### Running
* Under `Add-Ins` a button for `urdFusion` is present. Press it!
* Select whether you want to export all (visible) top-level components, or you want to select them manually. If the latter, select them
* Choose which component will become the URDF's base link
* Press Ok, and select a directory to save the STL, URDF and CSV files to.

## Development
* When the `urdFusion` button is pressed, all modules are reloaded. So any changes to modules will automatically be picked up.
* Changes to `urdFusion.py` will require the toggle (see [Usage](#usage)) to be turned off and back on. 
  * The only changes there should be when a new module is added.
  * Add the import, and then update `reloadModules`. The order matters, deeper reloads go in first.

## Roadmap
* Export joints
* Add materials to URDF (ie colors)
* Allow user to select colors for links
* Change "up" axis (z by default)

