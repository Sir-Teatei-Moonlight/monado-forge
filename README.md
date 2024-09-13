# Monado Forge
An addon for Blender (written with 3.3.1) for working with Xenoblade files. Adds a tab in the 3D view's right-hand toolbox with a bunch of useful features.

**General notice:** Keep the system console toggled on so you can see any potential warnings and non-fatal errors.

## Blender support
* **Blender 3.3.1** is the primary dev version. I do all work with this.
* **Blender 4.1.0** is the secondary dev version. I will make an effort to ensure everything works in it, but it isn't the main environment.

## Game support
* :no_entry_sign: - Believed to be nonexistent or unnecessary.
* :x: - Not supported, but planned (eventually).
* :hash: - Partially supported; number is a basic "how done does this feel" estimate.
* :o: - Not well-tested (if at all). _Ought_ to work just as well as the best-supported version, but no guarantees.
* :beginner: - Far from perfect, but works well enough that it can be considered "done" for the moment.
* :heavy_check_mark: - Supported. Any problems should be noted in the Known Issues section.

| | <img alt="XC1" src="https://www.xenoserieswiki.org/w/images/8/8d/Article_icon_-_Xenoblade_Chronicles.svg" width="24px"/> | <img alt="XCX" src="https://www.xenoserieswiki.org/w/images/3/3f/Article_icon_-_Xenoblade_Chronicles_X.svg" width="24px"/> | <img alt="XC2" src="https://www.xenoserieswiki.org/w/images/a/a8/Article_icon_-_Xenoblade_Chronicles_2.svg" width="24px"/> | <img alt="XC1DE" src="https://www.xenoserieswiki.org/w/images/6/6f/Article_icon_-_Xenoblade_Chronicles_Definitive_Edition.svg" width="24px"/> | <img alt="XC3" src="https://www.xenoserieswiki.org/w/images/b/bc/Article_icon_-_Xenoblade_Chronicles_3.svg" width="24px"/>
| --- | :---: | :---: | :---: | :---: | :---: |
| Skeleton import | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | 65% |
| Model import | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex colours | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ UVs | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex normals | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Vertex groups | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Shapes/Morphs | :no_entry_sign: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Outlines | :no_entry_sign: | :no_entry_sign: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Textures | :heavy_check_mark: | :x: | :heavy_check_mark: | :heavy_check_mark: | :o: |
| └ Materials | 50% | :x: | :beginner: | :beginner: | :o: |

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
* Choice of whether to import sharp edges as merged vertices or split vertices.
* Optionally imports outline data as a Solidify modifier, a vertex group (for the thickness factor), and a vertex colour (for...the colour).
* Optional mesh cleanup, erasing unused vertices, vertex groups, vertex colours, outline data, and shapes.
* Imports textures and saves them to a specified folder. By default, keeps only the biggest of each, but provides the option to keep all resolutions (using subfolders).
* Optionally differentiates newly-imported textures with same-named existing ones by appending the imported .wismt's filename.
* Optionally assumes that BC5 textures are normal maps, and auto-calculates the blue channel for them.
* Optionally automatically splits "temp" files into channels.
* Creates a basic material with all the correct textures and values in it, in which the first texture is assumed to be the base colour, and nothing else is plugged in. Also reads samplers to determine the textures' clamp/repeat, mirroring, and filtering settings, plugging textures into a UVPreProcess node accordingly (creating it if it doesn't exist already). Anything more will have to wait for deeper shader parsing.

#### Node Library
* Imports a couple preset node groups that are useful for many of these models, including:
  * Basic shader for metallic workflow
  * Basic shader for specular workflow
  * Shader for inset parallax effect (e.g. Core Crystals)
  * Node group for combining two normal maps "properly" (https://blog.selfshadow.com/publications/blending-in-detail/)

### Modify
#### Skeleton
* One-click setting all bones to be the same size.
* One-click flipping and mirroring bones so _L and _R sides match. Auto-mirror skips bones that seem like they might be intentionally uneven.
* One-click re-axis of bones, swapping their axes in any valid permutation.
* One-click renaming bones to move the _L/_R to the end, instead of sitting in the middle.
* All the above operate on the whole armature by default. Going into edit mode allows selecting individual bones to change.
* Merge two armatures, keeping only one copy of bones with the same name. Supports both "merge all" and "merge only if similar enough".

#### Mesh
* Link the shape keys of multiple meshes together using drivers.

## Known issues
Roughly in order of badness.
### Things with workarounds
* By default, images import as whatever the default colour setting is. It guesses whether they are non-colour data based on the name, so it can always get it wrong, and you'll have to manually notice and correct them. This will make them _look_ wrong, for whatever dumb reason, but they will _behave_ correctly.
  * .brres image names are not quite standardised enough to be worth doing this for them.
* Meshes with outlines are imported as two meshes, one with all the data (including the outline) and one with only the outline data. You have to pick whether to remove the outline from the main mesh, or delete the extra outline mesh.
* When importing .brres in Blender 4.1 with the "Add" duplicate image method, the incoming images are added as expected, but the resulting materials instead reference the originals. This is because Blender 4.1 broke the functionality of being able to nameswap "Thing.001" with an existing "Thing". You just have to switch the texture references manually, and hope the issue gets fixed in a later release.
### Things with no workarounds
#### All
* Blender does not respect raw integer colours. Every time we have to import a colour that isn't being put into an image file, we have to convert it into Blender's personal float colour format and hope that it decides to round correctly. As a result, off-by-one errors are likely and unavoidable without manual intervention.
* Blender does not support per-shape normals, so that information is lost. In theory it won't matter much.
#### .brres
* Some .brres features are not present because I've yet to encounter a XC1 model that uses them (and therefore cannot code or test them). This includes:
  * Face drawcodes for "quad", "tri fan", "lines", "line strip", and "points"
  * Face drawcodes with embedded data (as opposed to indexed data)
  * All but the most basic normals type (i.e. not anything based on tangent or bitangent)
  * Shapes/morphs
* When the duplicate image method is "Add", the new image is renamed to have the base name with no .001 distinguisher. This is the opposite of how it works with .wismt, where the existing images keep the base name. It doesn't really matter in practice, but it might trip you up if you're used to one and try the other.
#### .wimdo/wismt
* Many XC3 models for party members (and possibly others) appear to use an unknown parenting mechanism for several bones (believed to be constraint-related), so they end up not being parented at all. You'll have to guess how things need to be attached.
* Images that aren't power-of-two dimensions are not descrambled/deswizzled correctly. Very rare, but there.
* Models entirely embedded in the .wimdo are not checked for yet. (Normally, the model itself is in the .wismt and the .wimdo is just definitions, but putting a model in the .wimdo is also legal.) Very rare, so ought not to be a big deal.
* There's an extra bit of data that we don't know what it does. It shows up as a "29,4" warning in the console. You can ignore it.
* Everything assumes Eevee for rendering. I have no idea what will happen if you try to use Cycles.

## Planned features
Roughly in order of priority.
* UV folding (moving points to within the (0,1) range where possible)

