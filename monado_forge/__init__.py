import bpy

from bpy.types import AddonPreferences

bl_info = {
	"name": "Monado Forge",
	"description": "Xenoblade tools",
	"author": "Sir Teatei Moonlight (xenoserieswiki.org/tools) (https://github.com/Sir-Teatei-Moonlight)",
	"version": (0, 9, 0),
	"blender": (3, 3, 1),
	"category": "General",
}

from . skeleton import register,unregister

def register():
	skeleton.register()

def unregister():
	skeleton.unregister()

if __name__ == "__main__":
	register()

#[...]