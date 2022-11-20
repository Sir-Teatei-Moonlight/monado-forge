import bpy

from bpy.types import AddonPreferences

bl_info = {
	"name": "Monado Forge",
	"description": "Xenoblade tools",
	"author": "Sir Teatei Moonlight (xenoserieswiki.org/tools) (https://github.com/Sir-Teatei-Moonlight)",
	"version": (1, 0, 0),
	"blender": (3, 3, 1),
	"category": "General",
}

packageList = (
				"skeleton",
				)

register, unregister = bpy.utils.register_submodule_factory(__package__, packageList)

if __name__ == "__main__":
	register()

#[...]