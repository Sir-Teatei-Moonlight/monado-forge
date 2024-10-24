import bpy

from bpy.types import AddonPreferences

bl_info = {
	"name": "Monado Forge",
	"description": "Xenoblade tools",
	"author": "Sir Teatei Moonlight (https://github.com/Sir-Teatei-Moonlight) & others (https://github.com/Sir-Teatei-Moonlight/monado-forge/graphs/contributors)",
	"version": (7, 1, 0),
	"blender": (4, 1, 0),
	"category": "General",
}

packageList = (
				"classes",
				"utils",
				"utils_img",
				"main_ui",
				"import_funcs",
				"import_funcs_brres",
				"import_funcs_sar1",
				"import_ui",
				"modify_funcs",
				"modify_ui",
				)

register, unregister = bpy.utils.register_submodule_factory(__package__, packageList)

if __name__ == "__main__":
	register()

#[...]