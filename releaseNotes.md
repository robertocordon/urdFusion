# Release Notes

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
