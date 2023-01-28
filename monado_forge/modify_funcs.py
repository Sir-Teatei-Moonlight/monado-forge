import bpy
import math
import mathutils

from . classes import *
from . utils import *

def flip_selected_bones(self, context):
	angleEpsilon = context.scene.monado_forge_main.angleEpsilon
	for bone in bpy.context.selected_bones:
		roll = bone.roll
		bone.matrix = bone.matrix @ mathutils.Matrix([[-1,0,0,0],[0,-1,0,0],[0,0,-1,0],[0,0,0,1]])
		bone.roll = flipRoll(roll)
		clampBoneRoll(bone,angleEpsilon)
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

def merge_selected_to_active_armatures(self, context):
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
		for schmuck in toss:
			otherBones.remove(schmuck)
	# at this point, we have removed all the stuff we don't want to keep, so join the rest
	bpy.ops.object.mode_set(mode="OBJECT")
	bpy.ops.object.join()
	if outOfRangeCount > 0:
		self.report({"WARNING"}, "Kept "+str(outOfRangeCount)+" bones for being out of epsilon tolerance. See console for list.")
	return {"FINISHED"}

def register():
	pass

def unregister():
	pass

#[...]