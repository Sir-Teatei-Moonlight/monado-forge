# Monado Forge
An addon for Blender (written with 3.3.1) for working with Xenoblade files. Adds a tab in the 3D view's right-hand toolbox with a bunch of useful features.

**General notice:** Keep the system console toggled on so you can see any potential warnings.

## Game support
* :x: - Not supported, but planned (eventually).
* :hash: - Partially supported; number is a basic "how done does this feel" estimate.
* :o: - Not well-tested (if at all). _Ought_ to work just as well as the best-supported version, but no guarantees.
* :beginner: - Far from perfect, but works well enough that it can be considered "done" for the moment.
* :heavy_check_mark: - Supported. Any problems should be noted in the Known Issues section.

| | <img alt="XC1" src="https://www.xenoserieswiki.org/w/images/8/8d/Article_icon_-_Xenoblade_Chronicles.svg" width="24px"/> | <img alt="XCX" src="https://www.xenoserieswiki.org/w/images/3/3f/Article_icon_-_Xenoblade_Chronicles_X.svg" width="24px"/> | <img alt="XC2" src="https://www.xenoserieswiki.org/w/images/a/a8/Article_icon_-_Xenoblade_Chronicles_2.svg" width="24px"/> | <img alt="XC1DE" src="https://www.xenoserieswiki.org/w/images/6/6f/Article_icon_-_Xenoblade_Chronicles_Definitive_Edition.svg" width="24px"/> | <img alt="XC3" src="https://www.xenoserieswiki.org/w/images/b/bc/Article_icon_-_Xenoblade_Chronicles_3.svg" width="24px"/>
| --- | :---: | :---: | :---: | :---: | :---: |
| Skeleton import | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| Model import | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex colours | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ UVs | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex normals | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex groups | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Shapes/Morphs | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Textures | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Materials | :x: | :x: | :beginner: | :beginner: | :o: |

## Current features
### Import
#### General
* Controllable epsilon, for choosing whether 0.00001 should just be set to 0, and whether two things that differ by only that much should be treated as equal. Applies to position and rotation separately.

#### Skeleton
* Imports skeletons from .arc and .chr files.
* Choose whether to also import endpoints as bones, and puts them in a second bone layer.

#### Model
* Imports .wimdo/.wismt model files. The .wimdo can be imported alone, which grabs only whatever bones are inside, while the .wismt import requires a .wimdo to go with it.
* Supports normals, UVs, vertex colours, rigging (vertex groups), and shapes (morphs). Models are automatically parented to the skeleton found in the .wimdo; if there is no skeleton, they are parented to a blank one.
* By using the import-with-skeleton button instead, both the .wimdo's skeleton and the .arc/.chr skeleton will be imported, and then merged into one (giving the .arc/.chr one priority).
* Optionally also import lower-LOD models. Doesn't currently distinguish them in any way.
* Optional mesh cleanup, erasing unused vertices, vertex groups, and shapes.
* Imports textures and saves them to a specified folder. By default, keeps only the biggest of each, but provides the option to keep all resolutions (using subfolders). Supports all known-to-be-used formats (R8G8B8A8, BC1, BC3, BC4, BC5, BC7).
* Optionally assumes that BC5 textures are normal maps, and auto-calculates the blue channel for them.
* Differentiates newly-imported textures with same-named existing ones by appending the imported .wismt's filename. Can be turned off.
* Has the ability to automatically split "temp" files into channels, but currently does so in a terribly slow and inefficient way, so it's off by default. Don't exactly recommend using it yet, but it's there if you need it.
* Creates a basic material with all the correct textures and values in it, in which the first texture is assumed to be the base colour, and nothing else is plugged in. Anything more will have to wait for deeper shader parsing.

### Modify
* One-click flipping and mirroring bones so _L and _R sides match. Auto-mirror skips bones that seem like they might be intentionally uneven.
* Select individual bones for manual flipping/mirroring.
* One-click renaming bones to move the _L/_R to the end, instead of sitting in the middle.
* Merge two armatures, keeping only one copy of bones with the same name. Supports both "merge all" and "merge only if similar enough".

## Known issues
### Things with workarounds
* Some models have multiple weight tables, but the information about which one to use per each mesh cannot yet be found. Use the "Weight Table Override" feature to select which one to use for all meshes, and re-import for each one so you can pick-and-choose which ones are correct.
### Things with no workarounds
Roughly in order of badness.
* Blender does not support per-shape normals, so that information is lost. In theory it won't matter much.
* Models entirely embedded in the .wimdo are not checked for yet. Very rare, so ought not to be a big deal.
* Outline meshes are not recognised or treated as anything special. If you get two entirely identical meshes, consider that one may be the outline, in which case you can delete one of them (probably the one with no textures in its material). Unclear how to handle this as of yet (guessing it's material-related).
* Outline data is not yet processed. Not quite sure how to be honest, perhaps will leverage a vertex colour layer for it.
* Some materials only have a base colour (no textures). These import as the Actual Raw Colour Values, and so might look incorrect when Blender's colour spaces get involved. Don't ask me how to fix this.

## Planned features
Roughly in order of priority.
* UV folding

