import bpy
import time
from enum import Enum

# -----------------------------------------------------------------------------
# Core Constants and Enums
# -----------------------------------------------------------------------------

class ExportStatus(Enum):
    FRESH = 0   # Just exported (green) - less than 1 minute
    STALE = 1   # Exported a while ago (yellow) - less than 30 minutes
    NONE = 2    # No indicator needed - more than 30 minutes

# Timing constants
FRESH_DURATION = 60    # 1 minute in seconds
STALE_DURATION = 300   # 5 minutes in seconds

# Custom property names
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"
ORIGINAL_COLOR_PROP = "original_object_color"

# Export status colors
STATUS_COLORS = {
    ExportStatus.FRESH.value: (0.2, 0.8, 0.2, 1.0),  # Green
    ExportStatus.STALE.value: (0.8, 0.8, 0.2, 1.0),  # Yellow
}

# -----------------------------------------------------------------------------
# Export Status Tracking Functions
# -----------------------------------------------------------------------------

def mark_object_as_exported(obj):
    """Mark an object as just exported"""
    if obj is None or obj.type != "MESH":
        return
    
    # Set timestamp and status
    obj[EXPORT_TIME_PROP] = time.time()
    obj[EXPORT_STATUS_PROP] = ExportStatus.FRESH.value
    
    # Apply visual indicator
    set_object_color(obj)

def update_all_export_statuses():
    """Update status of all exported objects based on elapsed time"""
    current_time = time.time()
    updated_objects = False
    
    for obj in bpy.data.objects:
        if obj.type != "MESH" or EXPORT_TIME_PROP not in obj:
            continue
            
        # Calculate time since export
        elapsed_time = current_time - obj[EXPORT_TIME_PROP]
        old_status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
        
        # Determine new status
        if elapsed_time < FRESH_DURATION:
            new_status = ExportStatus.FRESH.value
        elif elapsed_time < STALE_DURATION:
            new_status = ExportStatus.STALE.value
        else:
            new_status = ExportStatus.NONE.value
            
        # Only update if status has changed
        if new_status != old_status:
            obj[EXPORT_STATUS_PROP] = new_status
            set_object_color(obj)
            updated_objects = True
            
            # Clean up if status has expired
            if new_status == ExportStatus.NONE.value:
                cleanup_export_props(obj)
    
    return updated_objects

def get_recently_exported_objects():
    """Get a list of recently exported objects sorted by export time"""
    exported_objects = []
    
    for obj in bpy.data.objects:
        if obj.type == "MESH" and EXPORT_TIME_PROP in obj:
            exported_objects.append((obj, obj[EXPORT_TIME_PROP]))
    
    # Sort by export time, most recent first
    return sorted(exported_objects, key=lambda x: x[1], reverse=True)

# -----------------------------------------------------------------------------
# Visual Indicator Functions
# -----------------------------------------------------------------------------

def set_object_color(obj):
    """Set object color based on its export status"""
    if EXPORT_STATUS_PROP not in obj:
        return
        
    status = obj[EXPORT_STATUS_PROP]
    
    # Ensure color attribute exists
    if not hasattr(obj, "color"):
        obj.color = (1.0, 1.0, 1.0, 1.0)
    
    # Store original color if not already saved
    if ORIGINAL_COLOR_PROP not in obj:
        obj[ORIGINAL_COLOR_PROP] = list(obj.color)
    
    # Apply color based on status
    if status in (ExportStatus.FRESH.value, ExportStatus.STALE.value):
        obj.color = STATUS_COLORS[status]
    else:
        # Restore original color
        restore_object_color(obj)
    
    # Ensure color is visible in viewport
    configure_viewport_for_object_colors()

def restore_object_color(obj):
    """Restore object's original color"""
    if ORIGINAL_COLOR_PROP in obj:
        obj.color = tuple(obj[ORIGINAL_COLOR_PROP])
        del obj[ORIGINAL_COLOR_PROP]

def configure_viewport_for_object_colors():
    """Configure viewport to display object colors"""
    try:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D" and hasattr(space, "shading"):
                        # Save original settings
                        if not hasattr(space.shading, "_original_settings"):
                            space.shading._original_settings = {
                                "type": space.shading.type,
                                "color_type": space.shading.color_type
                            }
                        
                        # Configure viewport
                        if space.shading.type not in ["SOLID", "MATERIAL"]:
                            space.shading.type = "SOLID"
                        space.shading.color_type = "OBJECT"
                        
                        # Enable object colors in outliner (Blender 4.0+)
                        prefs = getattr(bpy.context, "preferences", None)
                        if prefs and hasattr(prefs, "view"):
                            view = getattr(prefs.view, "show_object_viewport_color", None)
                            if view is not None:
                                prefs.view.show_object_viewport_color = True
    except Exception as e:
        print(f"Error configuring viewport: {e}")

def restore_viewport_settings():
    """Restore original viewport settings"""
    try:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D" and hasattr(space, "shading"):
                        if hasattr(space.shading, "_original_settings"):
                            original = space.shading._original_settings
                            space.shading.type = original.get("type", space.shading.type)
                            space.shading.color_type = original.get("color_type", "MATERIAL")
                            delattr(space.shading, "_original_settings")
    except Exception as e:
        print(f"Error restoring viewport: {e}")

def cleanup_export_props(obj):
    """Remove export-related properties from an object"""
    for prop in (EXPORT_TIME_PROP, EXPORT_STATUS_PROP):
        if prop in obj:
            del obj[prop]

# -----------------------------------------------------------------------------
# Timer Callback
# -----------------------------------------------------------------------------

def update_timer_callback():
    """Timer callback to periodically update export statuses"""
    try:
        if update_all_export_statuses():
            # Only redraw if something changed
            redraw_3d_views()
        return 10.0  # Check again in 10 seconds
    except Exception as e:
        print(f"Timer error: {e}")
        return 10.0  # Keep timer running even after errors

def redraw_3d_views():
    """Redraw all 3D views"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class MESH_OT_refresh_export_indicators(bpy.types.Operator):
    bl_idname = "mesh.refresh_export_indicators"
    bl_label = "Refresh Status"
    bl_description = "Manually refresh the export status indicators"
    
    def execute(self, context):
        update_all_export_statuses()
        redraw_3d_views()
        self.report({"INFO"}, "Export indicators refreshed")
        return {"FINISHED"}

class MESH_OT_clear_all_indicators(bpy.types.Operator):
    bl_idname = "mesh.clear_all_indicators"
    bl_label = "Clear All"
    bl_description = "Clear all export indicators"
    
    def execute(self, context):
        count = 0
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                if EXPORT_TIME_PROP in obj or EXPORT_STATUS_PROP in obj:
                    # Restore original color
                    restore_object_color(obj)
                    # Remove export properties
                    cleanup_export_props(obj)
                    count += 1
        
        redraw_3d_views()
        self.report({"INFO"}, f"Cleared indicators from {count} objects")
        return {"FINISHED"}

class MESH_OT_select_exported_object(bpy.types.Operator):
    bl_idname = "object.select_by_name"
    bl_label = "Select Object"
    bl_description = "Select this exported object"
    bl_options = {"REGISTER", "UNDO"}
    
    object_name: bpy.props.StringProperty(name="Object Name")
    
    def execute(self, context):
        # Deselect all objects
        bpy.ops.object.select_all(action="DESELECT")
        
        # Select and focus on target object
        obj = bpy.data.objects.get(self.object_name)
        if obj:
            obj.select_set(True)
            context.view_layer.objects.active = obj
            bpy.ops.view3d.view_selected(use_all_regions=False)
            
        return {"FINISHED"}

# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

operators = (
    MESH_OT_refresh_export_indicators,
    MESH_OT_clear_all_indicators,
    MESH_OT_select_exported_object,
)

def register():
    # Register operators
    for cls in operators:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Failed to register {cls.__name__}: {e}")
    
    # Start the timer
    try:
        if update_timer_callback not in bpy.app.timers.registered_timers():
            bpy.app.timers.register(update_timer_callback)
    except Exception as e:
        print(f"Failed to register timer: {e}")

def unregister():
    # Stop the timer
    try:
        if update_timer_callback in bpy.app.timers.registered_timers():
            bpy.app.timers.unregister(update_timer_callback)
    except Exception as e:
        print(f"Failed to unregister timer: {e}")
    
    # Restore original viewport settings
    try:
        restore_viewport_settings()
    except Exception as e:
        print(f"Failed to restore viewport settings: {e}")
    
    # Restore all objects' original colors
    try:
        for obj in bpy.data.objects:
            restore_object_color(obj)
            cleanup_export_props(obj)
    except Exception as e:
        print(f"Failed to restore object colors: {e}")
    
    # Unregister operators
    for cls in reversed(operators):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Failed to unregister {cls.__name__}: {e}")