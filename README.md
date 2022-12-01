# monado-forge
An addon for Blender (written with 3.3.1) for working with Xenoblade files.

## Current
### skeleton
* Imports skeletons from .arc and .chr files.
* Controllable epsilon, for choosing whether 0.00001 should just be set to 0, and whether a pair of bones that differ by only that much should be treated as equal.
* Choose whether to also import endpoints as bones, and puts them in a second bone layer.
* One-click flipping and mirroring bones so _L and _R sides match. Auto-mirror skips bones that seem like they might be intentionally uneven.
* Select individual bones for manual flipping/mirroring.
* One-click renaming bones to move the _L/_R to the end, instead of sitting in the middle.
* Merge two armatures, keeping only one copy of bones with the same name. Supports both "merge all" and "merge only if similar enough".

### model
* Imports .wimdo/.wismt model files. The .wimdo can be imported alone, which grabs only whatever bones are inside, while the .wismt import requires a .wimdo to go with it.
* Supports normals, UVs, vertex colours, and rigging. Models are automatically parented to the skeleton found in the .wimdo; use the skeleton merge feature to move it over to one imported form the matching .arc/.chr file.

## Planned
### model
* Shapes (morphs)
* Material assignment
* Better auto-naming of meshes

