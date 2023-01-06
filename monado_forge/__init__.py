import bpy

from bpy.types import AddonPreferences

bl_info = {
	"name": "Monado Forge",
	"description": "Xenoblade tools",
	"author": "Sir Teatei Moonlight (xenoserieswiki.org/tools) (https://github.com/Sir-Teatei-Moonlight)",
	"version": (3, 2, 3),
	"blender": (3, 3, 1),
	"category": "General",
}

packageList = (
				"utils",
				"ui",
				"skeleton",
				"model",
				)

register, unregister = bpy.utils.register_submodule_factory(__package__, packageList)

if __name__ == "__main__":
	register()

#[...]