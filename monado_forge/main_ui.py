import bpy
import math
from bpy.props import (
						BoolProperty,
						EnumProperty,
						FloatProperty,
						PointerProperty,
						)
from bpy.types import (
						Operator,
						Panel,
						PropertyGroup,
						)

class MonadoForgeProperties(PropertyGroup):
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
			context.scene.monado_forge_import.importEndpoints = True # not technically true, but conceptually true (endpoints are not a separate bone type, they're just in with the rest)

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
	positionEpsilon : FloatProperty(
		name="Position Epsilon",
		description="Positions less than this are set to zero; positions within this are considered equal for auto-mirroring",
		default=0.0001, # 1 micrometer
		min=0,
		max=0.001, # 1 milimeter - we're working on human scales, 1mm is significant no matter what
		soft_min=0,
		soft_max=0.001,
		unit="LENGTH",
	)
	angleEpsilon : FloatProperty(
		name="Angle Epsilon",
		description="Angles less than this are set to zero; angles within this are considered equal for auto-mirroring",
		default=math.radians(0.1),
		min=0,
		max=math.radians(1), # 1 degree is significant no matter how you look at it
		soft_min=0,
		soft_max=1,
		step=1,
		unit="ROTATION",
	)

class OBJECT_PT_MonadoForgePanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgePanel"
	bl_label = "Monado Forge"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Xenoblade"
	bl_context = ""

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)

class OBJECT_PT_MonadoForgeSettingsPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeSettingsPanel"
	bl_label = "Global Settings"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgePanel"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		col.prop(scn.monado_forge_main, "game")
		col.prop(scn.monado_forge_main, "printProgress")
		col.prop(scn.monado_forge_main, "positionEpsilon")
		col.prop(scn.monado_forge_main, "angleEpsilon")

classes = (
			MonadoForgeProperties,
			OBJECT_PT_MonadoForgePanel,
			OBJECT_PT_MonadoForgeSettingsPanel,
			)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	bpy.types.Scene.monado_forge_main = PointerProperty(type=MonadoForgeProperties)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.monado_forge_main

#[...]