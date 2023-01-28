import bpy

from bpy.types import AddonPreferences

bl_info = {
	"name": "Monado Forge",
	"description": "Xenoblade tools",
	"author": "Sir Teatei Moonlight (https://github.com/Sir-Teatei-Moonlight)",
	"version": (4, 1, 0),
	"blender": (3, 3, 1),
	"category": "General",
}

packageList = (
				"classes",
				"utils",
				"ui",
				"import",
				"modify",
				)

register, unregister = bpy.utils.register_submodule_factory(__package__, packageList)

if __name__ == "__main__":
	register()

#[...]