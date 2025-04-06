import bpy
import time
from bpy.types import Panel
from . import export_indicators

# Main UI Panel
class MESH_PT_exporter_panel(Panel):
    bl_label = "EasyMesh Batch Exporter"
    bl_idname = "MESH_PT_exporter_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter" # Match bl_info location

    # Helper functions
    def format_has_scale(self, format):
        # Check if the format is compatible with scale export setting
        return format in {"FBX", "OBJ", "STL"}

    def format_has_coordinates(self, format):
        # Check if the format is compatible with coordinate export settings
        return format in {"FBX", "OBJ", "USD", "STL"}


    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.use_property_split = True
        layout.use_property_decorate = False

        # Export path settings
        layout.prop(scene, "mesh_export_path")
        layout.prop(scene, "mesh_export_format")

        # Coordinate system settings
        if self.format_has_coordinates(scene.mesh_export_format):
            col = layout.column(heading="Coordinate system", align=True)
            row = col.row(align=True)
            row.prop(scene, "mesh_export_coord_up", expand=True)
            row = col.row(align=True)
            row.prop(scene, "mesh_export_coord_forward", expand=True)

        # Scale settings
        if self.format_has_scale(scene.mesh_export_format):
            col = layout.column(heading="Scale", align=True)
            col.prop(scene, "mesh_export_scale")

        col = layout.column(align=True)
        col.prop(scene, "mesh_export_zero_location")


        # Triangulate settings
        col = layout.column(heading="Triangulate", align=True)
        col.prop(scene, "mesh_export_triangulate")
        sub = col.column(align=True)
        sub.enabled = scene.mesh_export_triangulate # Enable/disable sub-options
        sub.prop(scene, "mesh_export_triangulate_method")
        sub.prop(scene, "mesh_export_keep_normals")

        # Rename file settings
        col = layout.column(heading="Rename file", align=True)
        col.prop(scene, "mesh_export_prefix")
        col.prop(scene, "mesh_export_suffix")

        layout.separator()

        # Export Button 
        mesh_count = sum(1 for obj in context.selected_objects if obj.type == "MESH")
        # col = layout.column(heading="Export Control", align=True)
        # box = col.box()
        # row = box.row()
        # row.label(text=f"Selected Meshes: {mesh_count}", icon="MESH_DATA")
        # Export button (always enabled unless poll() fails)
        row = layout.row()
        # Generate the button text first
        button_text = f"Export Meshes ({mesh_count})" if mesh_count > 0 else "Export Meshes"
        # Pass the generated text to the "text" parameter
        row.operator("mesh.batch_export", text=button_text, icon="EXPORT")


# LOD Panel (Keep as is, ensure bl_parent_id is correct)
class MESH_PT_exporter_panel_lod(Panel):
    bl_label = "LOD Generation"
    bl_idname = "MESH_PT_exporter_panel_lod"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI" 
    bl_category = "Exporter" 
    bl_parent_id = "MESH_PT_exporter_panel" 
    bl_options = {"DEFAULT_CLOSED"} # Optional: Start closed

    @classmethod
    def poll(cls, context):
         # Show only if the main panel exists
         return context.scene.mesh_export_path is not None

    def draw_header(self, context):
        layout = self.layout
        scene = context.scene
        layout.prop(scene, "mesh_export_lod", text="") # Checkbox in header

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False

        # Enable/disable based on the header checkbox
        layout.enabled = scene.mesh_export_lod

        col = layout.column(align=True)
        col.prop(scene, "mesh_export_lod_count")
        # Hide the decimate type bc I'm not sure if it's needed yet
        # col.prop(scene, "mesh_export_lod_type")

        box = layout.box()
        col = box.column(align=True)
        col.label(text="Ratios:")
        # Display relevant properties based on type
        if scene.mesh_export_lod_type == "COLLAPSE":
            col.prop(scene, "mesh_export_lod_ratio_01", text="LOD1")
            col.prop(scene, "mesh_export_lod_ratio_02", text="LOD2")
            col.prop(scene, "mesh_export_lod_ratio_03", text="LOD3")
            col.prop(scene, "mesh_export_lod_ratio_04", text="LOD4")
        elif scene.mesh_export_lod_type == "UNSUBDIVIDE":
            # Unsudivide should use Int for iterations
            col.prop(scene, "mesh_export_lod_ratio_01", text="LOD1 Iter.")
            col.prop(scene, "mesh_export_lod_ratio_02", text="LOD2 Iter.")
            col.prop(scene, "mesh_export_lod_ratio_03", text="LOD3 Iter.")
            col.prop(scene, "mesh_export_lod_ratio_04", text="LOD4 Iter.")


# Recent Exports Panel
class MESH_EXPORT_PT_recent_exports(Panel):
    bl_label = "Recent Exports"
    bl_idname = "MESH_EXPORT_PT_recent_exports"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter"
    bl_parent_id = "MESH_PT_exporter_panel"
    bl_options = {"DEFAULT_CLOSED"} # Optional: Start closed

    @classmethod
    def poll(cls, context):
        # Check if the indicator system is running and has data
        return hasattr(export_indicators, "get_recently_exported_objects")

    def draw(self, context):
        layout = self.layout

        try:
            # Use the function from the export_indicators module
            recently_exported = export_indicators.get_recently_exported_objects()
        except AttributeError:
            layout.label(text="Indicator system not fully loaded.")
            return

        if not recently_exported:
            layout.label(text="No recent mesh exports.")
            return

        # Keep as single combined list for now
        # Can separate into fresh/stale based on status if needed
        box = layout.box()
        col = box.column(align=True)

        max_items = 10 # Limit display length
        for i, (obj, export_time) in enumerate(recently_exported):
             if i >= max_items:
                  row = col.row()
                  row.label(text=f"... and {len(recently_exported) - max_items} more")
                  break

             if not obj: continue # Skip if object deleted

             row = col.row(align=True)
             icon = "HIDE_OFF" # Default icon

             # Button to select object
             op = row.operator("object.select_by_name", text="", icon=icon)
             op.object_name = obj.name # Custom operator needed here

             row.label(text=obj.name)

             # Time since export
             time_diff = time.time() - export_time
             if time_diff < 60:
                 time_str = f"{int(time_diff)}s ago"
             elif time_diff < 3600:
                 time_str = f"{int(time_diff/60)}m ago"
             else:
                 time_str = f"{int(time_diff/3600)}h ago"
             row.label(text=time_str)

        # Clear Indicators button if indicators are present
        if hasattr(export_indicators, "MESH_OT_clear_all_indicators"):
             layout.operator(export_indicators.MESH_OT_clear_all_indicators.bl_idname, icon="TRASH")



# Registration
classes = (
    MESH_PT_exporter_panel,
    MESH_PT_exporter_panel_lod,
    MESH_EXPORT_PT_recent_exports,
)

# register/unregister functions handled by __init__.py