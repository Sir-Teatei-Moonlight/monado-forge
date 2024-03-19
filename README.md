# Monado Forge
An addon for Blender (written with 3.3.1) for working with Xenoblade files. Adds a tab in the 3D view's right-hand toolbox with a bunch of useful features.

**General notice:** Keep the system console toggled on so you can see any potential warnings and non-fatal errors.

## Game support
* :x: - Not supported, but planned (eventually).
* :hash: - Partially supported; number is a basic "how done does this feel" estimate.
* :o: - Not well-tested (if at all). _Ought_ to work just as well as the best-supported version, but no guarantees.
* :beginner: - Far from perfect, but works well enough that it can be considered "done" for the moment.
* :heavy_check_mark: - Supported. Any problems should be noted in the Known Issues section.

| | <img alt="XC1" src="https://www.xenoserieswiki.org/w/images/8/8d/Article_icon_-_Xenoblade_Chronicles.svg" width="24px"/> | <img alt="XCX" src="https://www.xenoserieswiki.org/w/images/3/3f/Article_icon_-_Xenoblade_Chronicles_X.svg" width="24px"/> | <img alt="XC2" src="https://www.xenoserieswiki.org/w/images/a/a8/Article_icon_-_Xenoblade_Chronicles_2.svg" width="24px"/> | <img alt="XC1DE" src="https://www.xenoserieswiki.org/w/images/6/6f/Article_icon_-_Xenoblade_Chronicles_Definitive_Edition.svg" width="24px"/> | <img alt="XC3" src="https://www.xenoserieswiki.org/w/images/b/bc/Article_icon_-_Xenoblade_Chronicles_3.svg" width="24px"/>
| --- | :---: | :---: | :---: | :---: | :---: |
| Skeleton import | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | 65% |
| Model import | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex colours | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ UVs | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex normals | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex groups | 50% | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Shapes/Morphs | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Textures | :x: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Materials | :x: | :x: | :beginner: | :beginner: | :o: |

## Current features
Note that this list is of all features, not per-game features. Use the grid above, and known issues section below, to know what's currently supported per game.

### Import
#### General
* Controllable epsilon, for choosing whether 0.00001 should just be set to 0, and whether two things that differ by only that much should be treated as equal. Applies to position and rotation separately.

#### Skeleton
* Imports skeletons from .brres, .arc, and .chr files.
* Choose whether to also import endpoints as bones, and puts them in a second bone layer.

#### Model
* Imports .brres model files, with whatever model and skeleton is in there.
* Imports .wimdo/.wismt model files. The .wimdo can be imported alone, which grabs only whatever bones are inside, while the .wismt import requires a .wimdo to go with it.
* Supports normals, UVs, vertex colours, rigging (vertex groups), and shapes (morphs). Models are automatically parented to the skeleton found in the .wimdo; if there is no skeleton, they are parented to a blank one.
* By using the import-with-skeleton button instead, both the .wimdo's skeleton and the .arc/.chr skeleton will be imported, and then merged into one (giving the .arc/.chr one priority).
* Optionally also import lower-LOD models. Doesn't currently distinguish them in any way.
* Optional mesh cleanup, erasing unused vertices, vertex groups, vertex colours, and shapes.
* Imports textures and saves them to a specified folder. By default, keeps only the biggest of each, but provides the option to keep all resolutions (using subfolders). Supports all known-to-be-used formats (R8G8B8A8, BC1, BC3, BC4, BC5, BC7).
* Optionally differentiates newly-imported textures with same-named existing ones by appending the imported .wismt's filename.
* Optionally assumes that BC5 textures are normal maps, and auto-calculates the blue channel for them.
* Optionally automatically splits "temp" files into channels.
* Creates a basic material with all the correct textures and values in it, in which the first texture is assumed to be the base colour, and nothing else is plugged in. Also reads samplers to determine the textures' clamp/repeat, mirroring, and filtering settings, plugging textures into a TexMirrorXY node accordingly (creating it if it doesn't exist already). Anything more will have to wait for deeper shader parsing.

#### Node Library
* Imports a couple preset node groups that are useful for many of these models, including:
  * Basic shader for metallic workflow
  * Basic shader for specular workflow
  * Shader for inset parallax effect (e.g. Core Crystals)

### Modify
* One-click setting all bones to be the same size.
* One-click flipping and mirroring bones so _L and _R sides match. Auto-mirror skips bones that seem like they might be intentionally uneven.
* One-click renaming bones to move the _L/_R to the end, instead of sitting in the middle.
* All the above operate on the whole armature by default. Going into edit mode allows selecting individual bones to change.
* Merge two armatures, keeping only one copy of bones with the same name. Supports both "merge all" and "merge only if similar enough".

## Known issues
Roughly in order of badness.
### Things with workarounds
* By default, images import as whatever the default colour setting is. It guesses whether they are non-colour data based on the name, so it can always get it wrong, and you'll have to manually notice and correct them. This will make them _look_ wrong, for whatever dumb reason, but they will _behave_ correctly.
### Things with no workarounds
#### All
* Blender does not support per-shape normals, so that information is lost. In theory it won't matter much.
#### .brres
* Currently only supports meshes for which all vertices only have a single bone influence. Vertices that require multiple influences will be incorrect.
* Not all drawcodes are in yet.
#### .wimdo/wismt
* Many XC3 models for party members (and possibly others) appear to use an unknown parenting mechanism for several bones (believed to be constraint-related), so they end up not being parented at all. You'll have to guess how things need to be attached.
* Images that aren't power-of-two dimensions are not descrambled/deswizzled correctly. Very rare, but there.
* Models entirely embedded in the .wimdo are not checked for yet. (Normally, the model itself is in the .wismt and the .wimdo is just definitions, but putting a model in the .wimdo is also legal.) Very rare, so ought not to be a big deal.
* Outline meshes are not recognised or treated as anything special. If you get two entirely identical meshes, consider that one may be the outline, in which case you can delete one of them (probably the one with no textures in its material). Unclear how to automatically handle this, it's not immediately obvious how the game treats it (and guessing based on the name containing "outline" is not ideal).
* Outline data is not yet processed. Not quite sure how to be honest, perhaps will leverage a vertex colour layer for it.
* There's an extra bit of data that we don't know what it does. It shows up as a "29,4" warning in the console. You can ignore it.
* Some materials only have a base colour (no textures). These import as the Actual Raw Colour Values, and so might look incorrect when Blender's colour spaces get involved. Don't ask me how to fix this.

## Planned features
Roughly in order of priority.
* UV folding (moving points to within the (0,1) range where possible)

