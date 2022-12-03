# Monado Forge
An addon for Blender (written with 3.3.1) for working with Xenoblade files.

## Game support
* <img alt="XC1" src="https://www.xenoserieswiki.org/w/images/8/8d/Article_icon_-_Xenoblade_Chronicles.svg" width="20px"/> - Nothing yet. Existing .brres tools work mostly okay, so not a high priority.
* <img alt="XCX" src="https://www.xenoserieswiki.org/w/images/3/3f/Article_icon_-_Xenoblade_Chronicles_X.svg" width="20px"/> - Nothing yet. Another L for XCX fans :/
* <img alt="XC2" src="https://www.xenoserieswiki.org/w/images/a/a8/Article_icon_-_Xenoblade_Chronicles_2.svg" width="20px"/> - Current main development focus due to being the first (easiest) of the three Switch entries.
* <img alt="XC1DE" src="https://www.xenoserieswiki.org/w/images/6/6f/Article_icon_-_Xenoblade_Chronicles_Definitive_Edition.svg" width="20px"/> - Side main development focus.
* <img alt="XC3" src="https://www.xenoserieswiki.org/w/images/b/bc/Article_icon_-_Xenoblade_Chronicles_3.svg" width="20px"/> - Not being actively tested, but expected to mostly work.

## Current features
### Skeleton
* Imports skeletons from .arc and .chr files.
* Controllable epsilon, for choosing whether 0.00001 should just be set to 0, and whether a pair of bones that differ by only that much should be treated as equal. Applies to position and rotation separately.
* Choose whether to also import endpoints as bones, and puts them in a second bone layer.
* One-click flipping and mirroring bones so _L and _R sides match. Auto-mirror skips bones that seem like they might be intentionally uneven.
* Select individual bones for manual flipping/mirroring.
* One-click renaming bones to move the _L/_R to the end, instead of sitting in the middle.
* Merge two armatures, keeping only one copy of bones with the same name. Supports both "merge all" and "merge only if similar enough".

### Model
* Imports .wimdo/.wismt model files. The .wimdo can be imported alone, which grabs only whatever bones are inside, while the .wismt import requires a .wimdo to go with it.
* Supports normals, UVs, vertex colours, and rigging. Models are automatically parented to the skeleton found in the .wimdo; use the skeleton merge feature to move it over to one imported form the matching .arc/.chr file.
* Optionally also import lower-LOD models. Doesn't currently distinguish them in any way.

## Planned features
Roughly in order of priority.
* Model shapes/morphs
* Better auto-naming of meshes
* Texture extraction
* Material assignment

