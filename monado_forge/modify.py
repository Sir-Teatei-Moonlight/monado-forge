import bpy
import math
import mathutils
import traceback
from bpy.props import (
						BoolProperty,
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
			nonFinalMirror = context.scene.monado_forge_modify.nonFinalMirror
			angleEpsilon = context.scene.monado_forge_main.angleEpsilon
			skeleton = bpy.context.view_layer.objects.active.data
			bpy.ops.object.mode_set(mode="EDIT")
			editBones = skeleton.edit_bones
			flipCount = 0
			for bone in editBones:
				if bone.name.endswith("_R") or (nonFinalMirror and "_R_" in bone.name):
					roll = bone.roll
					bone.matrix = bone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]])
					bone.roll = flipRoll(roll)
					clampBoneRoll(bone,angleEpsilon)
					flipCount += 1
			bpy.ops.object.mode_set(mode="OBJECT")
			self.report({"INFO"}, "Flipped "+str(flipCount)+" bones.")
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
			angleEpsilon = context.scene.monado_forge_main.angleEpsilon
			for bone in bpy.context.selected_bones:
				roll = bone.roll
				bone.matrix = bone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]])
				bone.roll = flipRoll(roll)
				clampBoneRoll(bone,angleEpsilon)
			self.report({"INFO"}, "Flipped "+str(len(bpy.context.selected_bones))+" bones.")
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
			nonFinalMirror = context.scene.monado_forge_modify.nonFinalMirror
			positionEpsilon = context.scene.monado_forge_main.positionEpsilon
			angleEpsilon = context.scene.monado_forge_main.angleEpsilon
			skeleton = bpy.context.view_layer.objects.active.data
			bpy.ops.object.mode_set(mode="EDIT")
			editBones = skeleton.edit_bones
			mirroredCount = 0
			outOfRangeCount = 0
			for bone in editBones:
				if bone.name.endswith("_R") or (nonFinalMirror and "_R_" in bone.name):
					mirrorName = ""
					otherBone = None
					if "_R" in bone.name: mirrorName = bone.name.replace("_R","_L")
					if "_L" in bone.name: mirrorName = bone.name.replace("_L","_R")
					try:
						otherBone = editBones[mirrorName]
					except KeyError:
						otherBone = None
					if otherBone:
						canAutoMirror,message = isBonePairIdentical(bone,otherBone,positionEpsilon,angleEpsilon,mirrorable=True)
						if canAutoMirror:
							mirrorBone(bone,otherBone)
							mirroredCount += 1
						else:
							print(bone.name+" != "+otherBone.name+" ~ "+message)
							outOfRangeCount += 1
			bpy.ops.object.mode_set(mode="OBJECT")
			if outOfRangeCount > 0:
				self.report({"WARNING"}, "Mirrored "+str(mirroredCount)+" bones but skipped "+str(outOfRangeCount)+" for being out of epsilon tolerance. See console for list.")
			else:
				self.report({"INFO"}, "Mirrored "+str(mirroredCount)+" bones.")
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
			positionEpsilon = context.scene.monado_forge_main.positionEpsilon
			angleEpsilon = context.scene.monado_forge_main.angleEpsilon
			# edit mode is assumed (panel is edit mode limited)
			skeleton = bpy.context.view_layer.objects.active.data
			editBones = skeleton.edit_bones
			mirroredCount = 0
			outOfRangeCount = 0
			for bone in bpy.context.selected_bones:
				mirrorName = ""
				otherBone = None
				if "_R" in bone.name: mirrorName = bone.name.replace("_R","_L")
				if "_L" in bone.name: mirrorName = bone.name.replace("_L","_R")
				try:
					otherBone = editBones[mirrorName]
				except KeyError:
					otherBone = None
				if otherBone:
					canAutoMirror,message = isBonePairIdentical(bone,otherBone,positionEpsilon,angleEpsilon,mirrorable=True)
					if not canAutoMirror:
						print(bone.name+" != "+otherBone.name+" ~ "+message)
						outOfRangeCount += 1
					# but since the user selected this bone on purpose, we mirror it anyway
					mirrorBone(bone,otherBone)
					mirroredCount += 1
			if mirroredCount < len(bpy.context.selected_bones):
				self.report({"WARNING"}, "Did not mirror "+str(len(bpy.context.selected_bones)-mirroredCount)+" bones (no matching name on the other side).")
			if outOfRangeCount > 0:
				self.report({"WARNING"}, str(outOfRangeCount)+" bones were out of epsilon tolerance, but were mirrored anyway. See console for list.")
			else:
				self.report({"INFO"}, "Mirrored "+str(mirroredCount)+" bones.")
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
			skeleton = bpy.context.view_layer.objects.active.data
			bpy.ops.object.mode_set(mode="EDIT")
			editBones = skeleton.edit_bones
			count = 0
			for bone in editBones:
				# assumption: no bone can have both _L_ and _R_
				if "_L_" in bone.name:
					bone.name = bone.name.replace("_L_","_") + "_L"
					count += 1
				if "_R_" in bone.name:
					bone.name = bone.name.replace("_R_","_") + "_R"
					count += 1
			bpy.ops.object.mode_set(mode="OBJECT")
			self.report({"INFO"}, "Renamed "+str(count)+" bones.")
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
			# edit mode is assumed (panel is edit mode limited)
			skeleton = bpy.context.view_layer.objects.active.data
			editBones = skeleton.edit_bones
			count = 0
			for bone in bpy.context.selected_bones:
				# assumption: no bone can have both _L_ and _R_
				if "_L_" in bone.name:
					bone.name = bone.name.replace("_L_","_") + "_L"
					count += 1
				if "_R_" in bone.name:
					bone.name = bone.name.replace("_R_","_") + "_R"
					count += 1
			self.report({"INFO"}, "Renamed "+str(count)+" bones.")
		except Exception:
			traceback.print_exc()
			self.report({"ERROR"}, "Unexpected error; see console")
			return {"CANCELLED"}
		return {"FINISHED"}

class MonadoForgeMergeSelectedToActiveOperator(Operator):
	bl_idname = "object.monado_forge_merge_selected_to_active_operator"
	bl_label = "Xenoblade Skeleton Merge Selected To Active Operator"
	bl_description = "Joins armatures, merging bones of the same name"
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
			positionEpsilon = context.scene.monado_forge_main.positionEpsilon
			angleEpsilon = context.scene.monado_forge_main.angleEpsilon
			safeMerge = context.scene.monado_forge_modify.safeMerge
			# based on the poll above, we can assume all selected objects are armatures and there's more than one of them
			targetObject = context.view_layer.objects.active
			selectedObjects = context.view_layer.objects.selected
			# there doesn't seem to be a clean way to do this without invoking edit mode :/
			# at least we can have edit mode on multiple objects at once now
			bpy.ops.object.mode_set(mode="EDIT")
			targetBones = targetObject.data.edit_bones
			targetNameList = [b.name for b in targetBones]
			objsToDelete = []
			pruned = []
			outOfRangeCount = 0
			for otherObject in selectedObjects:
				if targetObject == otherObject: continue
				# move all the children right now to get it out of the way
				for c in otherObject.children:
					c.parent = targetObject
					for m in c.modifiers:
						if m.object == otherObject:
							m.object = targetObject
				otherBones = otherObject.data.edit_bones
				keep = []
				toss = []
				for otherBone in otherBones:
					if otherBone.name not in targetNameList:
						keep.append(otherBone)
						continue
					targetBone = targetBones[otherBone.name]
					areTheSame,message = isBonePairIdentical(targetBone,otherBone,positionEpsilon,angleEpsilon)
					if areTheSame or not safeMerge:
						toss.append(otherBone)
					else:
						print(targetObject.name+"."+targetBone.name+" != "+otherObject.name+"."+otherBone.name+" ~ "+message)
						outOfRangeCount += 1
						keep.append(otherBone)
				if len(keep) == -1:
					objsToDelete.append(otherObject)
					pruned.append(otherObject.name)
				else:
					for schmuck in toss:
						otherBones.remove(schmuck)
			for i in range(len(objsToDelete)):
				bpy.data.objects.remove(objsToDelete[i],do_unlink=True)
			if pruned:
				self.report({"INFO"}, "Removed "+str(len(pruned))+" object(s) for being entirely superfluous: "+", ".join(pruned))
			# at this point, we have removed all the stuff we don't want to keep, so join the rest
			bpy.ops.object.mode_set(mode="OBJECT")
			bpy.ops.object.join()
			if outOfRangeCount > 0:
				self.report({"WARNING"}, "Kept "+str(outOfRangeCount)+" bones for being out of epsilon tolerance. See console for list.")
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
		settingsPanel = col.column(align=True)
		settingsPanel.prop(scn.monado_forge_modify, "nonFinalMirror")
		modifyPanel = col.column(align=True)
		if activeObject and activeObject.mode == "EDIT":
			modifyPanel.operator(MonadoForgeBoneFlipSelectedOperator.bl_idname, text="Flip _R Bones", icon="ARROW_LEFTRIGHT")
			modifyPanel.operator(MonadoForgeBoneMirrorSelectedOperator.bl_idname, text="Mirror _R Bones", icon="MOD_MIRROR")
			modifyPanel.operator(MonadoForgeNonFinalLRFixSelectedOperator.bl_idname, text="Fix Non-Final L/R Names", icon="TRACKING_FORWARDS_SINGLE")
		else:
			modifyPanel.operator(MonadoForgeBoneFlipAllOperator.bl_idname, text="Flip _R Bones", icon="ARROW_LEFTRIGHT")
			modifyPanel.operator(MonadoForgeBoneMirrorAutoOperator.bl_idname, text="Mirror _R Bones", icon="MOD_MIRROR")
			modifyPanel.operator(MonadoForgeNonFinalLRFixAllOperator.bl_idname, text="Fix Non-Final L/R Names", icon="TRACKING_FORWARDS_SINGLE")
			modifyPanel.separator()
			modifyPanel.operator(MonadoForgeMergeSelectedToActiveOperator.bl_idname, text="Merge Selected to Active", icon="AUTOMERGE_ON")
			modifyPanel.prop(scn.monado_forge_modify, "safeMerge")

classes = (
			MonadoForgeBoneFlipAllOperator,
			MonadoForgeBoneFlipSelectedOperator,
			MonadoForgeBoneMirrorAutoOperator,
			MonadoForgeBoneMirrorSelectedOperator,
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