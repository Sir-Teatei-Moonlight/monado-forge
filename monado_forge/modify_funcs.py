import bpy
import math
import mathutils

from . classes import *
from . utils import *

def resize_selected_bones(self, context):
	targetLength = context.scene.monado_forge_modify.boneResizeSize
	for bone in bpy.context.selected_bones:
		bone.length = targetLength
	return {"FINISHED"}

def resize_all_bones_active_object(self, context):
	skeleton = bpy.context.view_layer.objects.active.data
	bpy.ops.object.mode_set(mode="EDIT")
	editBones = skeleton.edit_bones
	for bone in editBones:
		bone.select = True
	resize_selected_bones(self, context)
	for bone in editBones:
		bone.select = False
		bone.select_head = False
		bone.select_tail = False
	bpy.ops.object.mode_set(mode="OBJECT")
	return {"FINISHED"}

def flip_selected_bones(self, context):
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
	for bone in bpy.context.selected_bones:
		bone.matrix = bone.matrix @ mathutils.Matrix([[1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]])
	self.report({"INFO"}, "Flipped "+str(len(bpy.context.selected_bones))+" bones.")
	return {"FINISHED"}

def flip_all_r_bones_active_object(self, context):
	nonFinalMirror = context.scene.monado_forge_modify.nonFinalMirror
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
	skeleton = bpy.context.view_layer.objects.active.data
	bpy.ops.object.mode_set(mode="EDIT")
	editBones = skeleton.edit_bones
	flipCount = 0
	for bone in editBones:
		if bone.name.endswith("_R") or (nonFinalMirror and "_R_" in bone.name):
			bone.select = True
			flipCount += 1
		else:
			bone.select = False
	flip_selected_bones(self, context)
	for bone in editBones:
		bone.select = False
		bone.select_head = False
		bone.select_tail = False
	bpy.ops.object.mode_set(mode="OBJECT")
	self.report({"INFO"}, "Flipped "+str(flipCount)+" bones.")
	return {"FINISHED"}

def mirror_selected_bones(self, context, force=False):
	positionEpsilon = context.scene.monado_forge_main.positionEpsilon
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
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
			if mirrorName:
				print(bone.name+" is not mirrorable ("+mirrorName+" does not exist)")
			else:
				print(bone.name+" is not mirrorable (not _L or _R)")
			otherBone = None
		if otherBone:
			canAutoMirror,message = isBonePairIdentical(bone,otherBone,positionEpsilon,angleEpsilon,mirrorable=True)
			if canAutoMirror or force:
				mirrorBone(bone,otherBone)
				mirroredCount += 1
			if not canAutoMirror:
				print(bone.name+" != "+otherBone.name+" ~ "+message)
				outOfRangeCount += 1
	if mirroredCount < len(bpy.context.selected_bones):
		self.report({"WARNING"}, "Mirrored "+str(mirroredCount)+" bones but skipped "+str(len(bpy.context.selected_bones)-mirroredCount)+". See console for details.")
	else:
		self.report({"INFO"}, "Mirrored "+str(mirroredCount)+" bones.")
	return {"FINISHED"}

def mirror_all_r_bones_active_object(self, context):
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
			bone.select = True
		else:
			bone.select = False
	mirror_selected_bones(self, context)
	for bone in editBones:
		bone.select = False
		bone.select_head = False
		bone.select_tail = False
	bpy.ops.object.mode_set(mode="OBJECT")
	return {"FINISHED"}

def reaxis_selected_bones(self, context):
	newX = context.scene.monado_forge_modify.boneReAxisX
	newY = context.scene.monado_forge_modify.boneReAxisY
	newZ = context.scene.monado_forge_modify.boneReAxisZ
	axes = {
				"+X":[1,0,0,0],
				"+Y":[0,1,0,0],
				"+Z":[0,0,1,0],
				"-X":[-1,0,0,0],
				"-Y":[0,-1,0,0],
				"-Z":[0,0,-1,0],
			}
	for bone in bpy.context.selected_bones:
		bone.matrix = bone.matrix @ mathutils.Matrix([axes[newX],axes[newY],axes[newZ],[0,0,0,1]])
	self.report({"INFO"}, "Re-axised "+str(len(bpy.context.selected_bones))+" bones.")
	return {"FINISHED"}

def reaxis_all_bones_active_object(self, context):
	skeleton = bpy.context.view_layer.objects.active.data
	bpy.ops.object.mode_set(mode="EDIT")
	editBones = skeleton.edit_bones
	reaxisCount = 0
	for bone in editBones:
		bone.select = True
		reaxisCount += 1
	reaxis_selected_bones(self, context)
	for bone in editBones:
		bone.select = False
		bone.select_head = False
		bone.select_tail = False
	bpy.ops.object.mode_set(mode="OBJECT")
	self.report({"INFO"}, "Re-axised "+str(reaxisCount)+" bones.")
	return {"FINISHED"}

def fix_non_final_lr_selected_bones(self, context):
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
	return {"FINISHED"}

def fix_non_final_lr_bones_active_object(self, context):
	skeleton = bpy.context.view_layer.objects.active.data
	bpy.ops.object.mode_set(mode="EDIT")
	editBones = skeleton.edit_bones
	count = 0
	for bone in editBones:
		bone.select = True
	fix_non_final_lr_selected_bones(self, context)
	for bone in editBones:
		bone.select = False
	bpy.ops.object.mode_set(mode="OBJECT")
	return {"FINISHED"}

def merge_selected_to_active_armatures(self, context, force=False):
	# based on the UI calling this, we can assume all selected objects are armatures and there's more than one of them
	positionEpsilon = context.scene.monado_forge_main.positionEpsilon
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
	safeMerge = context.scene.monado_forge_modify.safeMerge
	targetObject = context.view_layer.objects.active
	selectedObjects = context.view_layer.objects.selected
	# there doesn't seem to be a clean way to do this without invoking edit mode :/
	# at least we can have edit mode on multiple objects at once now
	bpy.ops.object.mode_set(mode="EDIT")
	targetBones = targetObject.data.edit_bones
	targetNameList = [b.name for b in targetBones]
	outOfRangeCount = 0
	for otherObject in selectedObjects:
		if targetObject == otherObject: continue
		# move all the children right now to get it out of the way
		for c in otherObject.children:
			c.parent = targetObject
			for m in c.modifiers:
				if m.type == "ARMATURE" and m.object == otherObject:
					m.object = targetObject
		otherBones = otherObject.data.edit_bones
		for otherBone in otherBones:
			if otherBone.name not in targetNameList:
				continue
			targetBone = targetBones[otherBone.name]
			areTheSame,message = isBonePairIdentical(targetBone,otherBone,positionEpsilon,angleEpsilon)
			if areTheSame or not safeMerge or force:
				otherBone["mergeInto"] = targetBone.name
			else:
				print(targetObject.name+"."+targetBone.name+" != "+otherObject.name+"."+otherBone.name+" ~ "+message)
				outOfRangeCount += 1
	# decisions made, do the join
	bpy.ops.object.mode_set(mode="OBJECT")
	bpy.ops.object.join()
	# go back for every bone on which we assigned "mergeInto" and actually do said merge
	bpy.ops.object.mode_set(mode="EDIT")
	joinedBones = targetObject.data.edit_bones
	for bone in [j for j in joinedBones if "mergeInto" in j]:
		targetBone = joinedBones[bone["mergeInto"]]
		bone.parent = targetBone # so the deletion will automatically pass along parenting
		joinedBones.remove(bone)
	# done
	bpy.ops.object.mode_set(mode="OBJECT")
	if outOfRangeCount > 0:
		self.report({"WARNING"}, "Kept "+str(outOfRangeCount)+" bones for being out of epsilon tolerance. See console for list.")
	return {"FINISHED"}

def link_shape_keys(self, context):
	# based on the UI calling this, we can assume all selected objects are meshes and there's more than one of them
	baseObject = context.view_layer.objects.active
	selectedObjects = context.view_layer.objects.selected
	driverCount = 0
	for other in selectedObjects:
		if baseObject == other: continue
		for key in baseObject.data.shape_keys.key_blocks:
			try:
				otherKey = other.data.shape_keys.key_blocks[key.name]
			except KeyError:
				continue
			newDriverFCurve = otherKey.driver_add("value")
			newDriver = newDriverFCurve.driver
			newDriver.type = "AVERAGE"
			newVar = newDriver.variables.new()
			newVar.type = "SINGLE_PROP"
			newTarget = newVar.targets[0]
			newTarget.id_type = "KEY"
			newTarget.id = baseObject.data.shape_keys
			newTarget.data_path = f'key_blocks["{key.name}"].value'
			driverCount += 1
	self.report({"INFO"}, "Created "+str(driverCount)+" drivers.")
	return {"FINISHED"}

def register():
	pass

def unregister():
	pass

#[...]