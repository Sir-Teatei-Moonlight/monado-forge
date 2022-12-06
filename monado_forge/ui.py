import bpy
from bpy.props import (
						BoolProperty,
						EnumProperty,
						FloatProperty,
						PointerProperty,
						StringProperty,
						)
from bpy.types import (
						Operator,
						Panel,
						PropertyGroup,
						)

class XBToolsProperties(PropertyGroup):
	def gameListCallback(self, context):
		return (
			#("XC1","XC1","Xenoblade 1 (Wii)"),
			#("XCX","XCX","Xenoblade X"),
			("XC2","XC2","Xenoblade 2"),
			("XC1DE","XC1DE","Xenoblade 1 DE"),
			("XC3","XC3","Xenoblade 3"),
		)
	def gameListSelectionCallback(self, context):
		if self.game == "XC1":
			context.scene.xb_tools_skeleton.importEndpoints = True # not technically true, but conceptually true (endpoints are not a separate bone type, they're just in with the rest)

	game : EnumProperty(
		name="Game",
		items=gameListCallback,
		description="Game to deal with",
		default=1, #"XC1DE"
		update=gameListSelectionCallback,
	)
	printProgress : BoolProperty(
		name="Print Progress",
		description="Print info to console so it doesn't look like long-running operations are hung",
		default=True,
	)

class OBJECT_PT_XBToolsPanel(Panel):
	bl_idname = "OBJECT_PT_XBToolsPanel"
	bl_label = "Monado Forge"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Xenoblade"
	bl_context = ""

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.xb_tools, "game")
		col.prop(scn.xb_tools, "printProgress")

classes = (
			XBToolsProperties,
			OBJECT_PT_XBToolsPanel,
			)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	bpy.types.Scene.xb_tools = PointerProperty(type=XBToolsProperties)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.xb_tools

#[...]