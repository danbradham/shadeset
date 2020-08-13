# shadeset

Autodesk Maya scene shading exporter.


# Features

- Import and export shading based on hierarchy
- Supports custom shape attributes
- UI supporting asset based import and export

# UI

## Show the UI
```
import shadeset
shadeset.ui.show()
```

## Import
Apply shadesets that you've exported for specific assets.

1. Select the shadeset you'd like to apply
2. In your outliner, select the top transform of the hierarchy you'd like to apply it to.
3. Click apply.

<img src="https://github.com/danbradham/shadeset/blob/master/images/ui_import.png"/>

## Export
Export shadesets for an asset.

1. Apply some shaders.
2. Select the top level transform of the hierarchy that you'd like to export
shading data for.
3. Select the asset you'd like to export the shading data for.
4. Optionally provide a suffix like "red" or "green".
5. Click export.

<img src="https://github.com/danbradham/shadeset/blob/master/images/ui_export.png"/>

## Config
Configure the projects root directory and templates used to lookup assets
and publish root directories.

Templates must include {root}, {project} and {asset}. You may add additional
fields as needed. The publish template should start with your asset template
if you want to save shadesets into your asset folders.

<img src="https://github.com/danbradham/shadeset/blob/master/images/ui_config.png"/>

# API

### `gather(**kwargs)`
Gather shading data from a scene using all registered
`Subsets`.

Arguments:
- selection (bool): Gather shading data for the selected transforms

Returns:
- ShadeSet object containing the gathered shading data.


### `gather_hierarchy(**kwargs)`
Gather shading data from the selected hierarchies.


### `load(shade_path)`
Load a ShadeSet from disk.

Arguments:
- shade_path (str): Path to shadeset.yml file

Examples:
```
sset = load('some/shadeset.yml')
sset.apply(selection=True)
```

### `save(shade_set, outdir, name)`
Save a `Shadeset` to disk.

Arguments:
- shade_set (ShadeSet): shading data to save to write
- outdir (str): Output directory
- name (str): basename of Shadeset


### `register_subset(subset)`
Register a subset derived from `SubSet`.


### `unregister_subset(subset)`
Unregister a subset derived from `SubSet`.


### `clear_registry()`
Unregister all `SubSet`.
