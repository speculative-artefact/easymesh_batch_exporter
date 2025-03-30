import bpy
from bpy.types import Panel

# UI Panel
class MESH_PT_exporter_panel(Panel):
    bl_label = "Mesh Exporter"
    bl_idname = "MESH_PT_exporter_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Exporter"

    
    # def draw_header(self, context):
    #     layout = self.layout
    #     layout.label(text="Mesh Exporter")
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.use_property_split = True
        layout.use_property_decorate = False
        
        # Export path settings
        layout.prop(scene, "mesh_export_path")
        layout.prop(scene, "mesh_export_format")
        # layout.separator_spacer()
        
        # Transform settings
        if scene.mesh_export_format == "FBX" or scene.mesh_export_format == "OBJ":
            col = layout.column(heading="Coordinate system", align=True)
            col.prop(scene, "mesh_export_axis_simple")
            col = layout.column(heading="Scale", align=True)
            col.prop(scene, "mesh_export_scale")
        # col = layout.column(heading="Apply Transform", align=True)
        # col.prop(scene, "mesh_export_apply_location")
        # col.prop(scene, "mesh_export_apply_rotation")
        # col.prop(scene, "mesh_export_apply_scale")
        col = layout.column(align=True)
        col.prop(scene, "mesh_export_zero_location")
        if scene.mesh_export_format == "FBX" or scene.mesh_export_format == "OBJ":
            col = layout.column(align=True)
            col.prop(scene, "mesh_export_triangulate")
        # layout.separator_spacer()

        # Rename file settings
        col = layout.column(heading="Rename file", align=True)
        col.prop(scene, "mesh_export_prefix")
        col.prop(scene, "mesh_export_suffix")
        
        # Selection info
        mesh_count = sum(1 for obj in context.selected_objects 
                         if obj.type == 'MESH')
        col = layout.column(heading="Selected mesh objects", align=True)
        col.label(text=f"Selected mesh objects: {mesh_count}")
        
        # Export button
        # row = layout.row()
        # row.scale_y = 1.5
        layout.operator("mesh.batch_export", icon="EXPORT")

class MESH_PT_exporter_panel_lod(Panel):
    bl_label = "LODs"
    bl_idname = "MESH_PT_exporter_panel_lod"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Exporter"
    bl_parent_id = "MESH_PT_exporter_panel"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.use_property_split = True
        layout.use_property_decorate = False

        # LOD settings
        col = layout.column(heading="LOD config", align=True)
        col.prop(scene, "mesh_export_lod")
        if scene.mesh_export_lod > 0:
            col = layout.column(heading="LOD export settings", align=True)
            col.prop(scene, "mesh_export_lod_01")
            if scene.mesh_export_lod > 1:
                col.prop(scene, "mesh_export_lod_02")
            if scene.mesh_export_lod > 2:
                col.prop(scene, "mesh_export_lod_03")

classes = (
    MESH_PT_exporter_panel,
    MESH_PT_exporter_panel_lod,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)