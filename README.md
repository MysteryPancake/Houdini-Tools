# Houdini Tools
Scripts and tools I made at UTS Animal Logic Academy, mostly for data transfer between Blender and Houdini.

## [Houdini Tools](houdini_tools.py)

Tools designed to import data from Houdini into Blender.

![Houdini Tools](images/houdini_tools.PNG)

### Instances on Points

Blender's USD importer doesn't import instances correctly. It has two options: import realized geometry or import the points only.

Instances on Points fixes this, correctly importing instances as Blender should. It takes a point cloud and geometry to instance, imports the points as USD, then instances the geometry on each point using built-in collection instancing.

Blender's USD importer used to do this, but they removed it for some reason. Please add it back.

### Geometry and Attributes

Blender's Alembic importer is extremely limited. It ignores most geometry attributes and only imports vertex colors properly.

## [No Cloth Sims](no_cloth_sims.py)

A Blender addon I used extensively for the cloth FX in the short film [Coffee Brake](https://youtu.be/T57aCLYdX9M), named after the fact we weren't supposed to have cloth sims in the film.

![No Cloth Sims](images/no_cloth_sims.PNG)

It contains a bunch of utilities to speed up assembly for cloth FX. Its main purpose is adding a Mesh Sequence Cache to the tie, stripping the vertex weights and rebaking the Alembic in world space. This saved over 50 shots of manual work in the final film.

## [No Cloth Sims Lite](no_cloth_sims_lite.py)

A reduced version of No Cloth Sims I made for other departments to use. It was used for most shots in the [dimension sequence](https://youtu.be/T57aCLYdX9M?si=XX9xdrUEsF8jwQMv&t=102), where each artist made a unique scene based on a template animation. This saved another 15 shots of manual work.

![No Cloth Sims Lite](images/no_cloth_sims_lite.PNG)

## [Disable Subdivision](disable_subdiv.py)

A simple utility to disable subdivision on selected objects. I used it constantly to avoid giant Alembic files and mismatching topology.

![Disable Subdivision](images/disable_subdiv.PNG)
