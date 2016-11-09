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
import datetime
import io
import mathutils

class CalciumNoArmatureSelected(Exception):
  def __init__(self, value):
    self.value = value
  #end
  def __str__(self):
    return repr(self.value)
  #end
#endclass

class CalciumTooManyArmaturesSelected(Exception):
  def __init__(self, value):
    self.value = value
  #end
  def __str__(self):
    return repr(self.value)
  #end
#endclass

class CalciumExportFailed(Exception):
  def __init__(self, value):
    self.value = value
  #end
  def __str__(self):
    return repr(self.value)
  #end
#endclass

class CalciumKeyframe:
  index         = 0
  interpolation = 'LINEAR'
  easing        = 'IN_OUT'

  def __init__(self, _index, _interpolation, _easing):
    self.index         = _index
    self.interpolation = _interpolation
    self.easing        = _easing
  #end
#endclass

class CalciumExporter:
  __verbose     = False
  __axis_matrix = bpy_extras.io_utils.axis_conversion(to_forward='-Z', to_up='Y').to_4x4()
  __errors      = []

  def __init__(self, options):
    assert type(options) == type({})

    self.__verbose = options['verbose']
    assert type(self.__verbose) == bool
    self.__log("verbose logging enabled")

    self.__export_child_mesh_weights = options['export_child_mesh_weights']
    assert type(self.__export_child_mesh_weights) == bool
    self.__log("exporting child mesh weights enabled")
  #end

  def __log(self, fmt, *args):
    if True == self.__verbose:
      print("calcium: " + (fmt % args))
    #endif
  #end

  def __transformScaleToExport(self, v):
    assert type(v) == mathutils.Vector
    return mathutils.Vector((v.x, v.z, v.y))
  #end

  def __transformTranslationToExport(self, v):
    assert type(v) == mathutils.Vector
    return self.__axis_matrix * v
  #end

  def __transformOrientationToExport(self, q):
    assert type(q) == mathutils.Quaternion

    aa = q.to_axis_angle()
    axis = aa[0]
    axis = self.__axis_matrix * axis
    return mathutils.Quaternion(axis, aa[1])
  #end

  __supported_interpolation = {
    "CONSTANT" : "constant",
    "LINEAR"   : "linear",
    "EXPO"     : "exponential"
  }

  def __transformInterpolation(self, i):
    return self.__supported_interpolation.get(i, None)
  #end

  __supported_easing = {
    "EASE_IN"     : "in",
    "EASE_OUT"    : "out",
    "EASE_IN_OUT" : "in-out"
  }

  def __transformEasing(self, e):
    return self.__supported_easing.get(e, None)
  #end

  #
  # Check that for all keyframes k in a channel c, there is a corresponding
  # keyframe in all other channels at the same frame as k.
  #

  def __checkKeyframesCorresponding(self, action, group_name, group_channels):
    assert type(action) == bpy.types.Action
    assert type(group_name) == str
    assert type(group_channels) == type({})

    self.__log("[%s] __checkKeyframesCorresponding %s", action.name, group_name)

    ok = True
    for channel_name, channel_frames in group_channels.items():
      for channel_name_other, channel_frames_other in group_channels.items():

        if channel_name_other == channel_name:
          continue
        #endif

        for frame_index in channel_frames.keys():
          if not (frame_index in channel_frames_other):
            text =  "A keyframe for a channel of a group is missing corresponding keyframes in the other group channels.\n"
            text += "  Action:                        %s\n" % action.name
            text += "  Group:                         %s\n" % group_name
            text += "  Frame at:                      %d\n" % frame_index
            text += "  Channel:                       %s\n" % channel_name
            text += "  Channel with missing keyframe: %s\n" % channel_name_other
            text += "  Possible solution: Create a keyframe at frame %d for channel %s of group %s\n" % (frame_index, channel_name_other, group_name)
            self.__errors.append(text)
            ok = False
            continue
          #endif
        #endfor
      #endfor
    #endfor

    return ok
  #end

  #
  # Check that all of the given group channels have the same number of
  # keyframes.
  #

  def __checkKeyframesCountsEqual(self, action, group_name, group_channels):
    assert type(action) == bpy.types.Action
    assert type(group_name) == str
    assert type(group_channels) == type({})

    self.__log("[%s] __checkKeyframesCountsEqual %s", action.name, group_name)

    counts = {}
    for channel_name, channel in group_channels.items():
      assert type(channel_name) == str
      assert type(channel) == bpy.types.FCurve
      counts[channel_name] = len(channel.keyframe_points)
    #endfor

    uniques = len(set(counts.values()))
    if uniques > 1:
      text  = "The channels of a group have a different number of keyframes.\n"
      text += "  Action:                      %s\n" % action.name
      text += "  Group:                       %s\n" % group_name

      for channel_name, count in counts.items():
        text += "  Keyframe count for channel %s: %d\n" % (channel_name, count)
      #endfor

      text += "  Solution: Create a matching number of keyframes for all channels in the group\n"
      self.__errors.append(text)
      return False
    #endif

    assert uniques == 1
    return True
  #end

  #
  # Check that all of the channels of a given group are present. If none
  # of them are present, then the group is simply assumed not to exist and
  # ignored.
  #

  def __checkAllChannelsArePresent(self, action, group_name, group_channels):
    assert type(action) == bpy.types.Action
    assert type(group_name) == str
    assert type(group_channels) == type({})

    self.__log("[%s] __checkAllChannelsArePresent %s", action.name, group_name)

    #
    # If all of the channels are missing, then the group is simply assumed
    # not to exist.
    #

    missing = 0
    for channel_name, channel in group_channels.items():
      if channel == None:
        missing += 1
      #endif
    #endif

    self.__log("[%s] __checkAllChannelsArePresent %s: missing %d", action.name, group_name, missing)
    if missing == len(group_channels):
      self.__log("[%s] group %s has no keyframes, ignoring it", action.name, group_name)
      return False
    #endif

    #
    # However, if one or more channels are missing, then this is an error.
    #

    if missing > 0:
      for channel_name, channel in group_channels.items():
        text =  "No keyframes are defined for a channel of a group.\n"
        text += "  Action:   %s\n" % action.name
        text += "  Group:    %s\n" % group_name
        text += "  Channel:  %s\n" % channel_name
        text += "  Solution: Create the same number of keyframes for all channels of the group\n"
        self.__errors.append(text)
      #endfor
      return False
    #endif

    return True
  #end

  #
  # For the given group, collect all of the keyframes.
  #

  def __calculateKeyframesCollect(self, action, group_name, group_channels):
    assert type(action) == bpy.types.Action
    assert type(group_name) == str
    assert type(group_channels) == type({})

    self.__log("[%s] __calculateKeyframesCollect %s", action.name, group_name)

    keyframes_by_channel = {}
    for channel_name, channel in group_channels.items():
      assert type(channel_name) == str
      assert type(channel) == bpy.types.FCurve

      channel_frames = {}
      for frame in channel.keyframe_points:
        channel_frames[int(frame.co.x)] = frame
      #endfor
      keyframes_by_channel[channel_name] = channel_frames
    #endfor

    return keyframes_by_channel
  #end

  #
  # Collect all keyframes for export. This assumes that all of the other __calculateKeyframes
  # preconditions have been evaluated.
  #

  def __calculateKeyframesCollectForExport(self, action, group_name, keyframes_by_channel):
    assert type(action) == bpy.types.Action
    assert type(group_name) == str
    assert type(keyframes_by_channel) == type({})

    self.__log("[%s] __calculateKeyframesCollectForExport %s", action.name, group_name)

    error = False
    keyframes = {}
    for channel_name, channel_keyframes in keyframes_by_channel.items():
      for keyframe_index, keyframe in channel_keyframes.items():

        self.__log("[%s][%s][%d]: interpolation %s", action.name, group_name, keyframe_index, keyframe.interpolation)
        self.__log("[%s][%s][%d]: easing %s", action.name, group_name, keyframe_index, keyframe.easing)

        ex_interpolation = self.__transformInterpolation(keyframe.interpolation)
        if ex_interpolation == None:
          text = "The keyframe interpolation type is not supported.\n"
          text += "  Action:        %s\n" % action.name
          text += "  Group:         %s\n" % group_name
          text += "  Channel:       %s\n" % channel_name
          text += "  Keyframe:      %d\n" % keyframe_index
          text += "  Interpolation: %s\n" % keyframe.interpolation
          text += "  Possible solution: Use a supported interpolation type (%s)\n" % list(self.__supported_interpolation.values())
          self.__errors.append(text)
          error = True
        else:
          if keyframe_index in keyframes:
            existing = keyframes[keyframe_index]
            if existing != None:
              assert type(existing) == CalciumKeyframe

              if existing.interpolation != ex_interpolation:
                text  = "The interpolation value is not the same for all channels at this keyframe.\n"
                text += "  Action:                         %s\n" % action.name
                text += "  Group:                          %s\n" % group_name
                text += "  Channel:                        %s\n" % channel_name
                text += "  Keyframe:                       %d\n" % keyframe_index
                text += "  Interpolation:                  %s\n" % keyframe.interpolation
                text += "  Interpolation in other channel: %s\n" % existing.interpolation
                text += "  Possible solution: Set the interpolation value to %s for all channels at this keyframe\n" % existing.interpolation
                self.__errors.append(text)
                error = True
              #endif
            #endif
          #endif
        #endif

        ex_easing = self.__transformEasing(keyframe.easing)
        if ex_easing == None:
          text = "The keyframe easing type is not supported.\n"
          text += "  Action:        %s\n" % action.name
          text += "  Group:         %s\n" % group_name
          text += "  Channel:       %s\n" % channel_name
          text += "  Keyframe:      %d\n" % keyframe_index
          text += "  Interpolation: %s\n" % keyframe.easing
          text += "  Possible solution: Use a supported easing type (%s)\n" % list(self.__supported_easing.values())
          self.__errors.append(text)
          error = True
        else:
          if keyframe_index in keyframes:
            existing = keyframes[keyframe_index]
            if existing != None:
              assert type(existing) == CalciumKeyframe

              if existing.easing != ex_easing:
                text  = "The easing value is not the same for all channels at this keyframe.\n"
                text += "  Action:                         %s\n" % action.name
                text += "  Group:                          %s\n" % group_name
                text += "  Channel:                        %s\n" % channel_name
                text += "  Keyframe:                       %d\n" % keyframe_index
                text += "  Interpolation:                  %s\n" % keyframe.easing
                text += "  Interpolation in other channel: %s\n" % existing.easing
                text += "  Possible solution: Set the easing value to %s for all channels at this keyframe\n" % existing.easing
                self.__errors.append(text)
                error = True
              #endif
            #endif
          #endif
        #endif

        if not error:
          assert type(ex_interpolation) == str
          assert type(ex_easing) == str
          keyframes[keyframe_index] = CalciumKeyframe(keyframe_index, ex_interpolation, ex_easing)
        #endif
      #endfor
    #endfor

    if error:
      return None
    #endif

    return keyframes
  #end

  def __calculateKeyframesForCurves(self, action, group_name, group_channels):
    assert type(action) == bpy.types.Action
    assert type(group_name) == str
    assert type(group_channels) == type({})

    self.__log("[%s] __calculateKeyframesForCurves %s", action.name, group_name)

    if not self.__checkAllChannelsArePresent(action, group_name, group_channels):
      return None
    #endif

    if not self.__checkKeyframesCountsEqual(action, group_name, group_channels):
      return None
    #endif

    keyframes_by_channel = self.__calculateKeyframesCollect(action, group_name, group_channels)
    if not self.__checkKeyframesCorresponding(action, group_name, keyframes_by_channel):
      return None
    #endif

    return self.__calculateKeyframesCollectForExport(action, group_name, keyframes_by_channel)
  #end

  def __writeBoneCurvesTranslation(self, out_file, armature, action, bone_name):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature) == bpy_types.Object
    assert type(action) == bpy.types.Action
    assert armature.type == 'ARMATURE'
    assert type(bone_name) == str

    group_name          = 'pose.bones["%s"].location' % bone_name
    group_channels      = {}
    group_channels["X"] = action.fcurves.find(group_name, 0)
    group_channels["Y"] = action.fcurves.find(group_name, 1)
    group_channels["Z"] = action.fcurves.find(group_name, 2)

    frames = self.__calculateKeyframesForCurves(action, group_name, group_channels)

    if frames == None:
      return
    #endif

    frames_count = len(frames)
    self.__log("action[%s]: translation frame count: %d", action.name, frames_count)
    if frames_count > 0:
      out_file.write("    [curve\n")
      out_file.write("      [curve-bone \"%s\"]\n" % bone_name)
      out_file.write("      [curve-type translation]\n")
      out_file.write("      [curve-keyframes\n")

      assert bone_name in armature.pose.bones, "No bone %s in armature" % bone_name
      bone = armature.pose.bones[bone_name]

      for index in sorted(frames.keys()):
        assert type(index) == int
        frame = frames[index]
        assert type(frame) == CalciumKeyframe

        bpy.context.scene.frame_set(index)

        value = self.__transformTranslationToExport(bone.matrix.to_translation())
        out_file.write("        [curve-keyframe\n")
        out_file.write("          [curve-keyframe-index %d]\n" % index)
        out_file.write("          [curve-keyframe-interpolation \"%s\"]\n" % frame.interpolation)
        out_file.write("          [curve-keyframe-easing \"%s\"]\n" % frame.easing)
        out_file.write("          [curve-keyframe-vector3 %f %f %f]]\n" % (value.x, value.y, value.z))
      #end

      out_file.write("    ]]\n")
      out_file.write("\n")
    #endif
  #end

  def __writeBoneCurvesScale(self, out_file, armature, action, bone_name):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature) == bpy_types.Object
    assert type(action) == bpy.types.Action
    assert armature.type == 'ARMATURE'
    assert type(bone_name) == str

    group_name = 'pose.bones["%s"].scale' % bone_name
    group_channels      = {}
    group_channels["X"] = action.fcurves.find(group_name, 0)
    group_channels["Y"] = action.fcurves.find(group_name, 1)
    group_channels["Z"] = action.fcurves.find(group_name, 2)

    frames = self.__calculateKeyframesForCurves(action, group_name, group_channels)

    if frames == None:
      return
    #endif

    frames_count = len(frames)
    self.__log("action[%s]: scale frame count: %d", action.name, frames_count)
    if frames_count > 0:
      out_file.write("    [curve\n")
      out_file.write("      [curve-bone \"%s\"]\n" % bone_name)
      out_file.write("      [curve-type scale]\n")
      out_file.write("      [curve-keyframes\n")

      assert bone_name in armature.pose.bones, "No bone %s in armature" % bone_name
      bone = armature.pose.bones[bone_name]

      for index in sorted(frames.keys()):
        assert type(index) == int
        frame = frames[index]
        assert type(frame) == CalciumKeyframe

        bpy.context.scene.frame_set(index)

        value = self.__transformScaleToExport(bone.matrix.to_scale())
        out_file.write("        [curve-keyframe\n")
        out_file.write("          [curve-keyframe-index %d]\n" % index)
        out_file.write("          [curve-keyframe-interpolation \"%s\"]\n" % frame.interpolation)
        out_file.write("          [curve-keyframe-easing \"%s\"]\n" % frame.easing)
        out_file.write("          [curve-keyframe-vector3 %f %f %f]]\n" % (value.x, value.y, value.z))
      #end

      out_file.write("    ]]\n")
      out_file.write("\n")
    #endif
  #end

  def __writeBoneCurvesOrientation(self, out_file, armature, action, bone_name):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature) == bpy_types.Object
    assert type(action) == bpy.types.Action
    assert armature.type == 'ARMATURE'
    assert type(bone_name) == str

    group_name = 'pose.bones["%s"].rotation_quaternion' % bone_name
    group_channels      = {}
    group_channels["W"] = action.fcurves.find(group_name, 0)
    group_channels["X"] = action.fcurves.find(group_name, 1)
    group_channels["Y"] = action.fcurves.find(group_name, 2)
    group_channels["Z"] = action.fcurves.find(group_name, 3)

    frames = self.__calculateKeyframesForCurves(action, group_name, group_channels)

    if frames == None:
      return
    #endif

    frames_count = len(frames)
    self.__log("action[%s]: orientation frame count: %d", action.name, frames_count)
    if frames_count > 0:
      out_file.write("    [curve\n")
      out_file.write("      [curve-bone \"%s\"]\n" % bone_name)
      out_file.write("      [curve-type orientation]\n")
      out_file.write("      [curve-keyframes\n")

      assert bone_name in armature.pose.bones, "No bone %s in armature" % bone_name
      bone = armature.pose.bones[bone_name]

      for index in sorted(frames.keys()):
        assert type(index) == int
        frame = frames[index]
        assert type(frame) == CalciumKeyframe

        bpy.context.scene.frame_set(index)

        value = self.__transformOrientationToExport(bone.matrix.to_quaternion())
        out_file.write("        [curve-keyframe\n")
        out_file.write("          [curve-keyframe-index %d]\n" % index)
        out_file.write("          [curve-keyframe-interpolation \"%s\"]\n" % frame.interpolation)
        out_file.write("          [curve-keyframe-easing \"%s\"]\n" % frame.easing)
        out_file.write("          [curve-keyframe-quaternion-xyzw %f %f %f %f]]\n" % (value.x, value.y, value.z, value.w))
      #end

      out_file.write("    ]]\n")
      out_file.write("\n")
    #endif
  #end

  def __writeArmature(self, out_file, armature):
    assert type(armature) == bpy_types.Object
    assert armature.type == 'ARMATURE'
    self.__log("__writeArmature: %s", armature.name)

    out_file.write("[skeleton\n")
    out_file.write("  [skeleton-name \"%s\"]\n" % armature.name)
    out_file.write("  [skeleton-bones\n")

    for pose_bone in armature.pose.bones:
      bone        = pose_bone.bone
      bone_trans  = self.__transformTranslationToExport(bone.matrix_local.to_translation())
      bone_orient = self.__transformOrientationToExport(bone.matrix.to_quaternion())
      bone_scale  = self.__transformScaleToExport(bone.matrix_local.to_scale())

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

  def __writeActions(self, out_file, armature, actions):
    assert type(out_file) == io.TextIOWrapper
    assert type(actions) == bpy.types.bpy_prop_collection
    assert type(armature) == bpy_types.Object
    assert armature.type == 'ARMATURE'
    assert len(actions) > 0, "Must have at least one action"

    try:
      if armature.animation_data is not None:
        self.__log("__writeActions: saving action %s", armature.animation_data.action)
        saved_action = armature.animation_data.action
      else:
        self.__log("__writeActions: creating temporary animation data")
        armature.animation_data_create()
      #endif

      for action in actions:
        if action.name == 'poses':
          continue
        #endif

        self.__log("__writeActions: %s", action.name)
        armature.animation_data.action = action

        out_file.write("[action\n")
        out_file.write("  [action-name \"%s\"]\n" % action.name)
        out_file.write("  [action-length %d]\n" % int(action.frame_range.y - action.frame_range.x))
        out_file.write("  [curves\n")
        out_file.write("\n")

        for bone_name in armature.pose.bones.keys():
          self.__writeBoneCurvesTranslation(out_file, armature, action, bone_name)
          self.__writeBoneCurvesScale(out_file, armature, action, bone_name)
          self.__writeBoneCurvesOrientation(out_file, armature, action, bone_name)
        #end

        out_file.write("]]\n")
      #end

    finally:
      if saved_action:
        self.__log("__writeActions: restoring saved action %s", saved_action)
        armature.animation_data.action = saved_action
      else:
        self.__log("__writeActions: clearing temporary animation data")
        armature.animation_data_clear()
      #endif
    #endtry

    out_file.write("\n")
  #end

  #
  # Export all of the weights for a given mesh.
  #

  def __writeMeshWeights(self, out_file, mesh):
    assert type(out_file) == io.TextIOWrapper
    assert type(mesh) == bpy_types.Object
    assert mesh.type == 'MESH'

    self.__log("__writeMeshWeights: considering mesh %s for export", mesh.name)

    if len(mesh.vertex_groups) > 0:
      self.__log("__writeMeshWeights: exporting mesh %s", mesh.name)

      out_file.write("[mesh\n")
      out_file.write("  [mesh-name \"%s\"]\n" % mesh.name)
      out_file.write("  [mesh-weight-arrays\n")

      vertices = mesh.data.vertices
      vertex_count = len(vertices)

      for vertex_group in mesh.vertex_groups:
        self.__log("__writeMeshWeights: exporting %d weights for bone %s", vertex_count, vertex_group.name)

        out_file.write("      [mesh-weight-array\n")
        out_file.write("        [mesh-weight-array-bone \"%s\"]\n" % vertex_group.name)
        out_file.write("        [mesh-weight-array-values\n")

        for index in range (0, vertex_count):
          out_file.write("          [mesh-weight-array-value %f]\n" % vertex_group.weight(index))
        #endfor

        out_file.write("        ]\n")
        out_file.write("      ]\n")
      #endfor

      out_file.write("  ]\n")
      out_file.write("]\n")
    #endif
  #endif

  def __writeFile(self, out_file, armature):
    assert type(out_file) == io.TextIOWrapper
    assert type(armature) == bpy_types.Object
    assert armature.type == 'ARMATURE'

    out_file.write("[version 1 0]\n")
    out_file.write("[action-fps %d]\n" % bpy.context.scene.render.fps)

    self.__writeArmature(out_file, armature)

    for child in armature.children:
      if child.type == 'MESH':
        self.__writeMeshWeights(out_file, child)
      #endif
    #endfor

    if len(bpy.data.actions) > 0:
      frame_saved = bpy.context.scene.frame_current
      try:
        self.__writeActions(out_file, armature, bpy.data.actions)
      finally:
        bpy.context.scene.frame_set(frame_saved)
      #endtry
    #endif
  #end

  def __writeErrorLog(self, error_file, error_path, armature):
    assert type(error_file) == io.TextIOWrapper
    assert type(error_path) == str
    assert type(armature) == bpy_types.Object
    assert armature.type == 'ARMATURE'

    t = datetime.datetime.now()
    error_file.write("Export of %s on %s\n" % (armature.name, t.isoformat()))
    error_file.write("\n")

    if len(self.__errors) > 0:
      for error in self.__errors:
        error_file.write("%s\n" % error)
      #endfor

      error_file.write("\n")
      error_file.write("Export failed with %d errors.\n" % len(self.__errors))
      raise CalciumExportFailed("Exporting failed due to errors.\nSee the log file at: %s" % error_path)
    else:
      error_file.write("Exported successfully.\n")
    #endif
  #end

  def write(self, path):
    assert type(path) == str
    error_path = path + ".log"

    self.__errors = []

    armature = False
    if len(bpy.context.selected_objects) > 0:
      for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
          if armature:
            raise CalciumTooManyArmaturesSelected("Too many armatures selected: At most one of the selected objects can be an armature when exporting")
          #endif
          armature = obj
        #endif
      #endfor
    #endif

    if False == armature:
      raise CalciumNoArmatureSelected("No armatures selected: An armature object must be selected for export")
    #endif

    assert type(armature) == bpy_types.Object
    assert armature.type == 'ARMATURE'

    self.__log("opening: %s", path)
    with open(path, "wt") as out_file:
      self.__log("opening: %s", error_path)
      with open(error_path, "wt") as error_file:
        self.__writeFile(out_file, armature)
        self.__writeErrorLog(error_file, error_path, armature)
      #endwith
    #endwith
  #end

#endclass
