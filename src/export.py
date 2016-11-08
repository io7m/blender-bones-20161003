#
# Copyright © 2016 <code@io7m.com> http://io7m.com
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import bpy
import bpy_extras.io_utils
import bpy_types
import io
import mathutils

class CalciumExporter:
  __verbose     = False
  __axis_matrix = bpy_extras.io_utils.axis_conversion(to_forward='-Z', to_up='Y').to_4x4()

  def __init__(self, options):
    assert type(options) == type({})

    self.__verbose = options['verbose']
    assert type(self.__verbose) == bool
    self.__log("verbose logging enabled")
  #end

  def __log(self, fmt, *args):
    if True == self.__verbose:
      print("calcium: " + (fmt % args))
    #endif
  #end

  def __convertMatrix(self, m):
    return self.__axis_matrix * m
  #end

  def __convertQuaternion(self, q):
    aa = q.to_axis_angle()
    axis = aa[0]
    axis = self.__axis_matrix * axis
    return mathutils.Quaternion(axis, aa[1])
  #end

  def __writeBoneCurvesTranslation(self, out_file, armature_by_bone, action, bone_name):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature_by_bone) == type({})
    assert type(action) == bpy.types.Action
    assert type(bone_name) == str

    curve_name = 'pose.bones["%s"].location' % bone_name

    frames = {}
    curve_x = action.fcurves.find(curve_name, 0)
    curve_y = action.fcurves.find(curve_name, 1)
    curve_z = action.fcurves.find(curve_name, 2)

    if curve_x != None:
      for frame in curve_x.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_y != None:
      for frame in curve_y.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_z != None:
      for frame in curve_z.keyframe_points:
        frames[int(frame.co.x)] = True

    frames_count = len(frames)
    self.__log("action[%s]: translation frame count: %d", action.name, frames_count)
    if frames_count > 0:
      out_file.write("    [curve\n")
      out_file.write("      [curve-bone \"%s\"]\n" % bone_name)
      out_file.write("      [curve-type translation]\n")
      out_file.write("      [curve-keyframes\n")

      for index in sorted(frames.keys()):
        bpy.context.scene.frame_set(index)

        assert bone_name in armature_by_bone, "No armature for bone %s" % bone_name
        armature = armature_by_bone[bone_name]

        assert bone_name in armature.pose.bones, "No bone %s in armature" % bone_name
        bone = armature.pose.bones[bone_name]

        value = self.__convertMatrix(bone.matrix).to_translation()
        out_file.write("        [curve-keyframe\n")
        out_file.write("          [curve-keyframe-index %d]\n" % index)
        out_file.write("          [curve-keyframe-vector3 %f %f %f]]\n" % (value.x, value.y, value.z))
      #end

      out_file.write("    ]]\n")
      out_file.write("\n")
    #endif
  #end

  def __writeBoneCurvesScale(self, out_file, armature_by_bone, action, bone_name):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature_by_bone) == type({})
    assert type(action) == bpy.types.Action
    assert type(bone_name) == str

    curve_name = 'pose.bones["%s"].scale' % bone_name

    frames = {}
    curve_x = action.fcurves.find(curve_name, 0)
    curve_y = action.fcurves.find(curve_name, 1)
    curve_z = action.fcurves.find(curve_name, 2)

    if curve_x != None:
      for frame in curve_x.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_y != None:
      for frame in curve_y.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_z != None:
      for frame in curve_z.keyframe_points:
        frames[int(frame.co.x)] = True

    frames_count = len(frames)
    self.__log("action[%s]: scale frame count: %d", action.name, frames_count)
    if frames_count > 0:
      out_file.write("    [curve\n")
      out_file.write("      [curve-bone \"%s\"]\n" % bone_name)
      out_file.write("      [curve-type scale]\n")
      out_file.write("      [curve-keyframes\n")

      for index in sorted(frames.keys()):
        bpy.context.scene.frame_set(index)

        assert bone_name in armature_by_bone, "No armature for bone %s" % bone_name
        armature = armature_by_bone[bone_name]

        assert bone_name in armature.pose.bones, "No bone %s in armature" % bone_name
        bone = armature.pose.bones[bone_name]

        value = self.__convertMatrix(bone.matrix).to_scale()
        out_file.write("        [curve-keyframe\n")
        out_file.write("          [curve-keyframe-index %d]\n" % index)
        out_file.write("          [curve-keyframe-vector3 %f %f %f]]\n" % (value.x, value.y, value.z))
      #end

      out_file.write("    ]]\n")
      out_file.write("\n")
    #endif
  #end

  def __writeBoneCurvesOrientation(self, out_file, armature_by_bone, action, bone_name):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature_by_bone) == type({})
    assert type(action) == bpy.types.Action
    assert type(bone_name) == str

    curve_name = 'pose.bones["%s"].rotation_quaternion' % bone_name

    frames = {}
    curve_w = action.fcurves.find(curve_name, 0)
    curve_x = action.fcurves.find(curve_name, 1)
    curve_y = action.fcurves.find(curve_name, 2)
    curve_z = action.fcurves.find(curve_name, 3)

    if curve_x != None:
      for frame in curve_x.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_y != None:
      for frame in curve_y.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_z != None:
      for frame in curve_z.keyframe_points:
        frames[int(frame.co.x)] = True
    if curve_w != None:
      for frame in curve_w.keyframe_points:
        frames[int(frame.co.x)] = True

    frames_count = len(frames)
    self.__log("action[%s]: orientation frame count: %d", action.name, frames_count)
    if frames_count > 0:
      out_file.write("    [curve\n")
      out_file.write("      [curve-bone \"%s\"]\n" % bone_name)
      out_file.write("      [curve-type orientation]\n")
      out_file.write("      [curve-keyframes\n")

      for index in sorted(frames.keys()):
        bpy.context.scene.frame_set(index)

        assert bone_name in armature_by_bone, "No armature for bone %s" % bone_name
        armature = armature_by_bone[bone_name]

        assert bone_name in armature.pose.bones, "No bone %s in armature" % bone_name
        bone = armature.pose.bones[bone_name]

        value = self.__convertQuaternion(bone.matrix.to_quaternion())
        out_file.write("        [curve-keyframe\n")
        out_file.write("          [curve-keyframe-index %d]\n" % index)
        out_file.write("          [curve-keyframe-quaternion-xyzw %f %f %f %f]]\n" % (value.x, value.y, value.z, value.w))
      #end

      out_file.write("    ]]\n")
      out_file.write("\n")
    #endif
  #end

  def __collectArmatureObjects(self, all_objects):
    assert type(all_objects) == bpy.types.bpy_prop_collection
    assert (len(all_objects) > 0), "Must have at least one object in the scene"

    armature_objects = {}

    for obj in all_objects:
      if obj.type == 'ARMATURE':
        self.__log("_collectArmatureObjects: added %s", obj.name)
        assert (obj.name in armature_objects) == False, "Armature object %s already added" % obj.name
        armature_objects[obj.name] = obj
      #endif
    #end

    return armature_objects
  #end

  def __writeArmatures(self, out_file, armature_objects):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature_objects) == type({})
    assert (len(armature_objects) > 0), "Must have at least one armature"

    armature_by_bone = {}
    for armature_object_name, armature in armature_objects.items():
      assert type(armature) == bpy_types.Object
      assert armature.type == 'ARMATURE'
      self.__log("_writeArmatures: %s (%s)", armature_object_name, armature.name)

      out_file.write("[skeleton\n")
      out_file.write("  [skeleton-name \"%s\"]\n" % armature.name)
      out_file.write("  [skeleton-bones\n")

      for pose_bone in armature.pose.bones:
        bone = pose_bone.bone

        assert (bone.name in armature_by_bone) == False, "Bone name %s refers to more than one armature!" % bone.name
        armature_by_bone[bone.name] = armature

        bone_mat    = self.__convertMatrix(bone.matrix_local)
        bone_trans  = bone_mat.to_translation()
        bone_orient = self.__convertQuaternion(bone.matrix.to_quaternion())
        bone_scale  = bone_mat.to_scale()

        out_file.write("    [bone\n")
        out_file.write("      [bone-name             \"%s\"]\n" % bone.name)
        if bone.parent != None:
          out_file.write("      [bone-parent           \"%s\"]\n" % bone.parent.name)
        out_file.write("      [bone-translation      %f %f %f]\n" % (bone_trans.x, bone_trans.y, bone_trans.z))
        out_file.write("      [bone-scale            %f %f %f]\n" % (bone_scale.x, bone_scale.y, bone_scale.z))
        out_file.write("      [bone-orientation-xyzw %f %f %f %f]]\n" % (bone_orient.x, bone_orient.y, bone_orient.z, bone_orient.w))
      #end

      out_file.write("  ]\n")
      out_file.write("]\n")
    #end

    out_file.write("\n")
    return armature_by_bone
  #end

  def __writeActions(self, out_file, armature_by_bone, actions):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature_by_bone) == type({})
    assert type(actions) == bpy.types.bpy_prop_collection
    assert len(armature_by_bone) > 0, "Must have at least one armature"
    assert len(actions) > 0, "Must have at least one action"

    for action in actions:
      if action.name == 'poses':
        continue

      self.__log("_writeActions: %s", action.name)

      out_file.write("[action\n")
      out_file.write("  [name \"%s\"]\n" % action.name)
      out_file.write("  [curves\n")
      out_file.write("\n")

      for bone_name in armature_by_bone.keys():
        self.__writeBoneCurvesTranslation(out_file, armature_by_bone, action, bone_name)
        self.__writeBoneCurvesScale(out_file, armature_by_bone, action, bone_name)
        self.__writeBoneCurvesOrientation(out_file, armature_by_bone, action, bone_name)
      #end

      out_file.write("]]\n")
    #end

    out_file.write("\n")
  #end

  def __writeFile(self, out_file):
    assert type(out_file) == io.TextIOWrapper

    out_file.write("[version 1 0]\n")
    out_file.write("[action-fps %d]\n" % bpy.context.scene.render.fps)

    armature_objects = self.__collectArmatureObjects(bpy.data.objects)
    assert (len(armature_objects) > 0), "Must have at least one armature"

    armature_by_bone = self.__writeArmatures(out_file, armature_objects)
    assert (len(armature_by_bone) > 0), "Must have at least one bone"

    frame_saved = bpy.context.scene.frame_current
    self.__writeActions(out_file, armature_by_bone, bpy.data.actions)
    bpy.context.scene.frame_set(frame_saved)
  #end

  def write(self, path):
    assert type(path) == str

    self.__log("writing: %s", path)
    out_file = open(path, "wt")
    self.__writeFile(out_file)
    self.__log("closing: %s", path)
    out_file.close()
  #end

#endclass
