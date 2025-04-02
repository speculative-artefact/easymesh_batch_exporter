import bpy
import time
from bpy.types import Panel
from . import export_indicators
from .export_indicators import (
    ExportStatus, 
    EXPORT_STATUS_PROP, 
    get_recently_exported_objects
)

# Main UI Panel
class MESH_PT_exporter_panel(Panel):
    bl_label = "Mesh Exporter"
    bl_idname = "MESH_PT_exporter_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter"

    
    def format_has_scale(self, format):
        # Check if the format is compatible with scale
        if format in {"FBX", "OBJ", "STL"}:
            return True
        return False
    

    def format_has_coordinates(self, format):
        # Check if the format is compatible with coordinates
        if format in {"FBX", "OBJ", "USD", "STL"}:
            return True
        return False
    

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
            col.prop(scene, "mesh_export_axis_simple")
        # Scale settings
        if self.format_has_scale(scene.mesh_export_format):
            col = layout.column(heading="Scale", align=True)
            col.prop(scene, "mesh_export_scale")
        col = layout.column(align=True)
        col.prop(scene, "mesh_export_zero_location")

        # Triangulate settings
        col = layout.column(heading="Triangulate", align=True)
        col.prop(scene, "mesh_export_triangulate")
        col = layout.column(align=True)
        if not scene.mesh_export_triangulate:
            col.enabled = False
        col.prop(scene, "mesh_export_triangulate_method")
        col.prop(scene, "mesh_export_keep_normals")

        # Rename file settings
        col = layout.column(heading="Rename file", align=True)
        col.prop(scene, "mesh_export_prefix")
        col.prop(scene, "mesh_export_suffix")
        
        # Export button and progress indicator
        layout.separator()
        
        # Export button - disabled during export
        row = layout.row()
        row.enabled = not scene.mesh_export_in_progress
        row.operator("mesh.batch_export", icon="EXPORT")
        
        # Show progress when exporting
        if scene.mesh_export_in_progress:
            box = layout.box()
            row = box.row()
            
            # Progress message
            if scene.mesh_export_total > 0:
                progress_text = f"Exporting {scene.mesh_export_progress}/{scene.mesh_export_total}: {scene.mesh_export_current_object}"
                row.label(text=progress_text, icon="TEMP")
                
                # Add visual progress bar
                # progress = scene.mesh_export_progress / max(scene.mesh_export_total, 1)
                # box.prop(scene, "mesh_export_progress", text="Progress", slider=True)
            else:
                row.label(text="Export in progress...", icon="TEMP")
                
        layout.separator()

# LOD settings
class MESH_PT_exporter_panel_lod(Panel):
    bl_label = "LODs"
    bl_idname = "MESH_PT_exporter_panel_lod"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
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

# Panel to display selection info and select all meshes 
class MESH_PT_exporter_panel_selection(Panel):
    bl_label = "Selection"
    bl_idname = "MESH_PT_exporter_panel_selection"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter"
    bl_parent_id = "MESH_PT_exporter_panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Selection info
        mesh_count = sum(1 for obj in context.selected_objects if obj.type == "MESH")
        col = layout.column(heading="Selected mesh objects", align=True)
        row = col.row(align=True)
        row.label(text=f"Mesh objects: {mesh_count}")
        # row.label(text=f"Vertices: {sum(len(obj.data.vertices) for obj in context.selected_objects if obj.type == "MESH")}")
        row.operator("mesh.select_all_meshes", icon="RESTRICT_SELECT_OFF", text="Select all meshes")

        # Select all meshes button
        # col = layout.column(heading="Select all", align=True)
        # col = layout.row()
        # col.operator("mesh.select_all_meshes", icon="RESTRICT_SELECT_OFF", text="Select all meshes")

# Panel to display recently exported objects
class MESH_EXPORT_PT_recent_exports(bpy.types.Panel):
    bl_label = "Recent Exports"
    bl_idname = "MESH_EXPORT_PT_recent_exports"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter"  # Match your main panel's category
    bl_parent_id = "MESH_PT_exporter_panel"
    bl_options = {"DEFAULT_CLOSED"}
    
    def draw(self, context):
        layout = self.layout
        
        recent_exports = get_recently_exported_objects()
        
        if not recent_exports:
            layout.label(text="No recent exports")
            return
        
        # Add a refresh button
        row = layout.row()
        row.operator("mesh.refresh_export_indicators", icon="FILE_REFRESH")
        row.operator("mesh.clear_all_indicators", icon="X")
        
        # Group exports by status
        fresh_exports = []
        stale_exports = []
        
        for obj, export_time in recent_exports:
            status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
            if status == ExportStatus.FRESH.value:
                fresh_exports.append((obj, export_time))
            elif status == ExportStatus.STALE.value:
                stale_exports.append((obj, export_time))
        
        # Display fresh exports
        if fresh_exports:
            box = layout.box()
            box.label(text="Recent Exports (< 1 min)", icon="RADIOBUT_ON")
            
            for obj, export_time in fresh_exports:
                row = box.row(align=True)
                
                # Calculate time since export
                time_diff = time.time() - export_time
                time_str = f"{int(time_diff)}s ago"
                
                # Object name with button to select it
                op = row.operator("object.select_by_name", text=obj.name, icon="MESH_DATA")
                op.object_name = obj.name
                
                # Time since export
                row.label(text=time_str)
        
        # Display stale exports
        if stale_exports:
            box = layout.box()
            box.label(text="Older Exports (< 5 min)", icon="KEYFRAME")
            
            for obj, export_time in stale_exports[:5]:  # Limit to 5 older items
                row = box.row(align=True)
                
                # Calculate time since export
                time_diff = time.time() - export_time
                if time_diff < 3600:
                    time_str = f"{int(time_diff/60)}m ago"
                else:
                    time_str = f"{int(time_diff/3600)}h ago"
                
                # Object name with button to select it
                op = row.operator("object.select_by_name", text=obj.name, icon="MESH_DATA")
                op.object_name = obj.name
                
                # Time since export
                row.label(text=time_str)

classes = (
    MESH_PT_exporter_panel,
    MESH_PT_exporter_panel_lod,
    MESH_PT_exporter_panel_selection,
    MESH_EXPORT_PT_recent_exports,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)