# Release Notes

## [v0.5] (2026-05-08)

* Support for adding values for damping, friction, effort and velocity

## [v0.4] (2026-05-08)

* Support for materials (ie colors) on the URDF meshes. Options include using material colors, alternating pre-set colors (rainbow), and solid single colors
* Support for custom collision meshes, or using the same mesh, or no mesh
* A lot of quality of life improvements including dialog value persistence
* Lots of code cleanup

## [v0.3] (2026-05-07)

* We now export a URDF file containing all link info and joints
* Added an checkbox to make STL export optional

## [v0.2] (2026-05-06)

* User is prompted for an output directory
* The csv is exported into that directory
* And STL directory is created, and an STL per link is created in it

## [v0.1] (2026-05-06)

* The main UI has been implemented, it allows the choosing of the components that will become links, and the base link.
* The add-in makes certain sanity checks, and collects all the data for the component: origin, mass, center of mass and inertial vectors
* It exports all the data to a CSV file
