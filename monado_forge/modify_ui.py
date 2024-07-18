import bpy
import math
import mathutils
import traceback
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

from . classes import *
from . utils import *
from . modify_funcs import *

def getCrossAxis(x,y):
	# no need to be fancy, just precompute it all
	crossProducts = {
						"+X+Y":"+Z",
						"+X+Z":"-Y",
						"+X-Y":"-Z",
						"+X-Z":"+Y",
						"+Y+X":"-Z",
						"+Y+Z":"+X",
						"+Y-X":"+Z",
						"+Y-Z":"-X",
						"+Z+X":"+Y",
						"+Z+Y":"-X",
						"+Z-X":"-Y",
						"+Z-Y":"+X",
						"-X+Y":"-Z",
						"-X+Z":"+Y",
						"-X-Y":"+Z",
						"-X-Z":"-Y",
						"-Y+X":"+Z",
						"-Y+Z":"-X",
						"-Y-X":"-Z",
						"-Y-Z":"+X",
						"-Z+X":"-Y",
						"-Z+Y":"+X",
						"-Z-X":"+Y",
						"-Z-Y":"-X",
					}
	try:
		return crossProducts[x+y]
	except KeyError:
		return ""


class MonadoForgeBoneResizeAllOperator(Operator):
	bl_idname = "object.monado_forge_bone_resize_all_operator"
	bl_label = "Xenoblade Skeleton Bone Resize All Operator"
	bl_description = "Resizes all bones to the given length"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode == "POSE": return False
		return True
	
	def execute(self, context):
		try:
			resize_all_bones_active_object(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneResizeSelectedOperator(Operator):
	bl_idname = "object.monado_forge_bone_resize_selected_operator"
	bl_label = "Xenoblade Skeleton Bone Resize Selected Operator"
	bl_description = "Resizes all selected bones to tthe given length"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode != "EDIT": return False
		return True
	
	def execute(self, context):
		try:
			# edit mode is assumed (button is edit mode limited)
			resize_selected_bones(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneFlipAllOperator(Operator):
	bl_idname = "object.monado_forge_bone_flip_all_operator"
	bl_label = "Xenoblade Skeleton Bone Flip All Operator"
	bl_description = "Flips all _R bones, pointing them the other way (reversible)"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode == "POSE": return False
		return True
	
	def execute(self, context):
		try:
			flip_all_r_bones_active_object(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneFlipSelectedOperator(Operator):
	bl_idname = "object.monado_forge_bone_flip_selected_operator"
	bl_label = "Xenoblade Skeleton Bone Flip Selected Operator"
	bl_description = "Flips all selected bones, pointing them the other way (reversible)"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode != "EDIT": return False
		return True
	
	def execute(self, context):
		try:
			# edit mode is assumed (button is edit mode limited)
			flip_selected_bones(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneMirrorAutoOperator(Operator):
	bl_idname = "object.monado_forge_bone_mirror_auto_operator"
	bl_label = "Xenoblade Skeleton Bone Mirror Auto Operator"
	bl_description = "Edits all _R bones to mirror the _L bones of the same name (destructive)"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode == "POSE": return False
		return True
	
	def execute(self, context):
		try:
			mirror_all_r_bones_active_object(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneMirrorSelectedOperator(Operator):
	bl_idname = "object.monado_forge_bone_mirror_selected_operator"
	bl_label = "Xenoblade Skeleton Bone Mirror Selected Operator"
	bl_description = "Edits all selected bones to mirror the bones of the same name with reverse L/R polarity (destructive)"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode != "EDIT": return False
		return True
	
	def execute(self, context):
		try:
			# edit mode is assumed (button is edit mode limited)
			mirror_selected_bones(self, context, force=True)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneReAxisAllOperator(Operator):
	bl_idname = "object.monado_forge_bone_reaxis_all_operator"
	bl_label = "Xenoblade Skeleton Bone Re-Axis All Operator"
	bl_description = "Re-axis all bones, preserving angle"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode == "POSE": return False
		if not getCrossAxis(context.scene.monado_forge_modify.boneReAxisX,context.scene.monado_forge_modify.boneReAxisY): return False
		return True
	
	def execute(self, context):
		try:
			reaxis_all_bones_active_object(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeBoneReAxisSelectedOperator(Operator):
	bl_idname = "object.monado_forge_bone_reaxis_selected_operator"
	bl_label = "Xenoblade Skeleton Bone Re-Axis Selected Operator"
	bl_description = "Re-axis all selected bones, preserving angle"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode != "EDIT": return False
		if not getCrossAxis(context.scene.monado_forge_modify.boneReAxisX,context.scene.monado_forge_modify.boneReAxisY): return False
		return True
	
	def execute(self, context):
		try:
			# edit mode is assumed (button is edit mode limited)
			reaxis_selected_bones(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeNonFinalLRFixAllOperator(Operator):
	bl_idname = "object.monado_forge_non_final_lr_fix_all_operator"
	bl_label = "Xenoblade Skeleton Non Final LR Fix All Operator"
	bl_description = "Edits all bone names to put the _L/_R at the end"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode == "POSE": return False
		return True
	
	def execute(self, context):
		try:
			fix_non_final_lr_bones_active_object(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeNonFinalLRFixSelectedOperator(Operator):
	bl_idname = "object.monado_forge_non_final_lr_fix_selected_operator"
	bl_label = "Xenoblade Skeleton Non Final LR Fix Selected Operator"
	bl_description = "Edits selected bone names to put the _L/_R at the end"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode != "EDIT": return False
		return True
	
	def execute(self, context):
		try:
			# edit mode is assumed (button is edit mode limited)
			fix_non_final_lr_selected_bones(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeMergeSelectedToActiveOperator(Operator):
	bl_idname = "object.monado_forge_merge_selected_to_active_operator"
	bl_label = "Xenoblade Skeleton Merge Selected To Active Operator"
	bl_description = "Joins selected armatures into the active one, merging bones of the same name"
	bl_options = {"REGISTER","UNDO"}
	
	@classmethod
	def poll(cls, context):
		activeObject = context.view_layer.objects.active
		selectedObjects = context.view_layer.objects.selected
		if not activeObject: return False
		if activeObject.type != "ARMATURE": return False
		if activeObject.mode != "OBJECT": return False
		if len(selectedObjects) < 2: return False
		for s in selectedObjects:
			if s.type != "ARMATURE": return False
			if s.mode != "OBJECT": return False
		return True
	
	def execute(self, context):
		try:
			merge_selected_to_active_armatures(self, context)
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeViewModifyToolsProperties(PropertyGroup):
	nonFinalMirror : BoolProperty(
		name="Accept Non-Final L/R",
		description="Treat non-final _L_ and _R_ in bone names as being mirrored",
		default=True,
	)
	boneResizeSize : FloatProperty(
		name="Bone Resize",
		description="New length of bones",
		default=0.1,
		min=0.01,
		soft_min=0.01,
		soft_max=10,
		unit="LENGTH",
	)
	def reaxisSelectCallback(self, context):
		crossAxis = getCrossAxis(self.boneReAxisX,self.boneReAxisY)
		if crossAxis:
			self.boneReAxisZ = crossAxis
		else:
			self.boneReAxisZ = "Invalid!"
	def reAxisListCallback(self, context):
		return (
			("+X","+X","+X"),
			("+Y","+Y","+Y"),
			("+Z","+Z","+Z"),
			("-X","-X","-X"),
			("-Y","-Y","-Y"),
			("-Z","-Z","-Z"),
		)
	boneReAxisX : EnumProperty(
		name="New +X",
		items=reAxisListCallback,
		description="Change the current +X axis to this axis",
		default=0,
		update=reaxisSelectCallback,
	)
	boneReAxisY : EnumProperty(
		name="New +Y",
		items=reAxisListCallback,
		description="Change the current +Y axis to this axis",
		default=1,
		update=reaxisSelectCallback,
	)
	boneReAxisZ : StringProperty(
		name="New +Z",
		description="Change the current +Z axis to this axis",
		default="+Z",
	)
	safeMerge : BoolProperty(
		name="Safe Merge",
		description="Only merges bones of the same name if they have the same position and rotation (false: merge them no matter what)",
		default=True,
	)

class OBJECT_PT_MonadoForgeViewModifyPanel(Panel):
	bl_idname = "OBJECT_PT_MonadoForgeViewModifyPanel"
	bl_label = "Modify"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "OBJECT_PT_MonadoForgePanel"

	def draw(self, context):
		layout = self.layout
		scn = context.scene
		col = layout.column(align=True)
		activeObject = bpy.context.view_layer.objects.active
		col.label(text="Skeleton")
		settingsPanel = col.column(align=True) # note to self: remove this later when non-skeleton modifiers exist (and thus there are subpanels)
		settingsPanel.prop(scn.monado_forge_modify, "nonFinalMirror")
		modifyPanel = col.column(align=True)
		settingsPanel.prop(scn.monado_forge_modify, "boneResizeSize")
		if activeObject and activeObject.mode == "EDIT":
			modifyPanel.operator(MonadoForgeBoneResizeSelectedOperator.bl_idname, text="Resize Selected Bones", icon="FIXED_SIZE")
			modifyPanel.separator()
			modifyPanel.operator(MonadoForgeBoneFlipSelectedOperator.bl_idname, text="Flip Selected Bones", icon="ARROW_LEFTRIGHT")
			modifyPanel.operator(MonadoForgeBoneMirrorSelectedOperator.bl_idname, text="Mirror Selected Bones", icon="MOD_MIRROR")
			modifyPanel.separator()
			self.reaxisPanel(scn,modifyPanel)
			modifyPanel.operator(MonadoForgeBoneReAxisSelectedOperator.bl_idname, text="Re-Axis Selected Bones", icon="EMPTY_ARROWS")
			modifyPanel.separator()
			modifyPanel.operator(MonadoForgeNonFinalLRFixSelectedOperator.bl_idname, text="Fix Non-Final L/R Names", icon="TRACKING_FORWARDS_SINGLE")
		else:
			modifyPanel.operator(MonadoForgeBoneResizeAllOperator.bl_idname, text="Resize Bones", icon="FIXED_SIZE")
			modifyPanel.separator()
			modifyPanel.operator(MonadoForgeBoneFlipAllOperator.bl_idname, text="Flip _R Bones", icon="ARROW_LEFTRIGHT")
			modifyPanel.operator(MonadoForgeBoneMirrorAutoOperator.bl_idname, text="Mirror _R Bones", icon="MOD_MIRROR")
			modifyPanel.separator()
			self.reaxisPanel(scn,modifyPanel)
			modifyPanel.operator(MonadoForgeBoneReAxisAllOperator.bl_idname, text="Re-Axis Bones", icon="EMPTY_ARROWS")
			modifyPanel.separator()
			modifyPanel.operator(MonadoForgeNonFinalLRFixAllOperator.bl_idname, text="Fix Non-Final L/R Names", icon="TRACKING_FORWARDS_SINGLE")
			modifyPanel.separator()
			modifyPanel.operator(MonadoForgeMergeSelectedToActiveOperator.bl_idname, text="Merge Selected to Active", icon="AUTOMERGE_ON")
			modifyPanel.prop(scn.monado_forge_modify, "safeMerge")
	
	def reaxisPanel(self,scn,modifyPanel):
		basePanel = modifyPanel.row(align=True)
		xPanel = basePanel.column(align=True)
		xPanel.label(text="+X")
		xPanel.prop(scn.monado_forge_modify, "boneReAxisX", text="")
		yPanel = basePanel.column(align=True)
		yPanel.label(text="+Y")
		yPanel.prop(scn.monado_forge_modify, "boneReAxisY", text="")
		zPanel = basePanel.column(align=True)
		zPanel.label(text="+Z")
		zPanel.prop(scn.monado_forge_modify, "boneReAxisZ", text="")
		zPanel.enabled = False

classes = (
			MonadoForgeBoneResizeAllOperator,
			MonadoForgeBoneResizeSelectedOperator,
			MonadoForgeBoneFlipAllOperator,
			MonadoForgeBoneFlipSelectedOperator,
			MonadoForgeBoneMirrorAutoOperator,
			MonadoForgeBoneMirrorSelectedOperator,
			MonadoForgeBoneReAxisAllOperator,
			MonadoForgeBoneReAxisSelectedOperator,
			MonadoForgeNonFinalLRFixAllOperator,
			MonadoForgeNonFinalLRFixSelectedOperator,
			MonadoForgeMergeSelectedToActiveOperator,
			MonadoForgeViewModifyToolsProperties,
			OBJECT_PT_MonadoForgeViewModifyPanel,
			)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

	bpy.types.Scene.monado_forge_modify = PointerProperty(type=MonadoForgeViewModifyToolsProperties)

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
	del bpy.types.Scene.monado_forge_modify

#[...]