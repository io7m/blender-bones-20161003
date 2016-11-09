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

bl_info = {
  "name":        "Calcium format",
  "author":      "io7m",
  "version":     (0, 0, 2),
  "blender":     (2, 66, 0),
  "location":    "File > Export > Calcium (.ca)",
  "description": "Export armatures and actions.",
  "warning":     "",
  "wiki_url":    "",
  "tracker_url": "",
  "category":    "Import-Export"
}

import bpy

class ExportCalcium(bpy.types.Operator):
  bl_idname = "export_scene.ca"
  bl_label = "Export Calcium"

  filepath                  = bpy.props.StringProperty(subtype='FILE_PATH')
  verbose                   = bpy.props.BoolProperty(name="Verbose logging",description="Enable verbose debug logging",default=True)
  export_child_mesh_weights = bpy.props.BoolProperty(name="Export child meshes",description="Export the vertex weights of the child meshes of the armature",default=True)

  def execute(self, context):
    self.filepath = bpy.path.ensure_ext(self.filepath, ".ca")

    args = {}
    args['verbose'] = self.verbose
    assert type(args['verbose']) == bool

    args['export_child_mesh_weights'] = self.export_child_mesh_weights
    assert type(args['export_child_mesh_weights']) == bool

    from . import export
    e = export.CalciumExporter(args)

    try:
      e.write(self.filepath)
    except export.CalciumNoArmatureSelected as ex:
      self.report({'ERROR'}, ex.value)
    except export.CalciumTooManyArmaturesSelected as ex:
      self.report({'ERROR'}, ex.value)
    except export.CalciumExportFailed as ex:
      self.report({'ERROR'}, ex.value)
    #endtry

    return {'FINISHED'}
  #end

  def invoke(self, context, event):
    if not self.filepath:
      self.filepath = bpy.path.ensure_ext(bpy.data.filepath, ".ca")
    context.window_manager.fileselect_add(self)
    return {'RUNNING_MODAL'}
  #end
#endclass

def menuFunction(self, context):
  self.layout.operator(ExportCalcium.bl_idname, text="Calcium (.ca)")
#end

def register():
  bpy.utils.register_class(ExportCalcium)
  bpy.types.INFO_MT_file_export.append(menuFunction)
#end

def unregister():
  bpy.utils.unregister_class(ExportCalcium)
  bpy.types.INFO_MT_file_export.remove(menuFunction)
#end

if __name__ == "__main__":
  register()
#endif

