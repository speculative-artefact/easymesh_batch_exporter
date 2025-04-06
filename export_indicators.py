import bpy
import time
from enum import Enum
from bpy.types import Operator # Keep for clear/select operators if used

# --- Keep Core Constants and Enums ---
class ExportStatus(Enum):
    FRESH = 0   # Just exported (green) - less than 1 minute
    STALE = 1   # Exported a while ago (yellow) - less than 5 minutes (adjusted from 30)
    NONE = 2    # No indicator needed - more than 5 minutes

# Timing constants
FRESH_DURATION = 60    # 1 minute in seconds
STALE_DURATION = 300   # 5 minutes in seconds

# Custom property names (ensure consistency with operators.py)
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"
ORIGINAL_COLOR_PROP = "original_object_color" # For visual indicator

# Export status colors
STATUS_COLORS = {
    ExportStatus.FRESH.value: (0.2, 0.8, 0.2, 1.0),  # Green
    ExportStatus.STALE.value: (0.8, 0.8, 0.2, 1.0),  # Yellow
}

# --- REMOVED: mark_object_as_exported(obj) --- -> Moved to operators.py


# --- Keep Status Update Logic ---
def update_all_export_statuses():
    """Update status of all exported objects based on elapsed time"""
    current_time = time.time()
    updated_objects = False

    for obj in bpy.data.objects:
        if obj.type != "MESH" or EXPORT_TIME_PROP not in obj:
            continue

        export_time = obj.get(EXPORT_TIME_PROP, 0)
        if not export_time: continue # Skip if timestamp missing

        elapsed_time = current_time - export_time
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
            set_object_color(obj) # Update visual indicator
            updated_objects = True

            # Clean up if status has expired
            if new_status == ExportStatus.NONE.value:
                cleanup_export_props(obj)

    return updated_objects


# --- Keep Recent Objects List Logic ---
def get_recently_exported_objects():
    """Get a list of recently exported objects sorted by export time"""
    exported_objects = []

    for obj in bpy.data.objects:
         # Check for the timestamp property and ensure status is not NONE
        if obj.type == "MESH" and EXPORT_TIME_PROP in obj:
             status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
             if status != ExportStatus.NONE.value:
                  exported_objects.append((obj, obj[EXPORT_TIME_PROP]))

    # Sort by export time, most recent first
    return sorted(exported_objects, key=lambda x: x[1], reverse=True)


# --- Keep Visual Indicator Functions (Coloring, Viewport Config) ---
def set_object_color(obj):
    """Set object color based on its export status"""
    if EXPORT_STATUS_PROP not in obj:
        return

    status = obj[EXPORT_STATUS_PROP]

    # Ensure color attribute exists (should always exist on objects)
    # Store original color if not already saved and status requires color change
    if ORIGINAL_COLOR_PROP not in obj and status != ExportStatus.NONE.value:
        obj[ORIGINAL_COLOR_PROP] = list(obj.color)

    # Apply color based on status
    if status in STATUS_COLORS:
        obj.color = STATUS_COLORS[status]
        # Ensure object color is visible in viewport
        obj.show_instancer_for_viewport = True # Might be needed depending on Blender version/settings
    else:
        # Restore original color if status is NONE
        restore_object_color(obj)

    # Configure viewport globally (might be better done once on register)
    # configure_viewport_for_object_colors()


def restore_object_color(obj):
    """Restore object's original color"""
    if ORIGINAL_COLOR_PROP in obj:
        try:
            obj.color = tuple(obj[ORIGINAL_COLOR_PROP])
            # Optionally remove the stored original color property
            del obj[ORIGINAL_COLOR_PROP]
        except (ReferenceError, KeyError):
             pass # Object might be gone or prop removed


def cleanup_export_props(obj):
     """Remove export tracking properties when status expires"""
     props_to_remove = [EXPORT_TIME_PROP, EXPORT_STATUS_PROP, ORIGINAL_COLOR_PROP]
     for prop in props_to_remove:
          if prop in obj:
               try:
                   del obj[prop]
               except (ReferenceError, KeyError):
                   pass # Object/prop might be gone


# --- Viewport Configuration ---
# Store original settings per 3D view space
_original_shading_settings = {}

def configure_viewport_for_object_colors():
    """Configure active 3D viewport to display object colors in Solid mode."""
    global _original_shading_settings
    try:
        # Find active 3D view
        area = next((a for a in bpy.context.screen.areas if a.type == "VIEW_3D"), None)
        if not area: return
        space = next((s for s in area.spaces if s.type == "VIEW_3D"), None)
        if not space or not hasattr(space, "shading"): return

        # Store original settings if not already stored for this space
        if space.v3d.id_data not in _original_shading_settings:
             _original_shading_settings[space.v3d.id_data] = {
                 "type": space.shading.type,
                 "color_type": space.shading.color_type
             }

        # Configure viewport only if needed
        if space.shading.type == "SOLID" and space.shading.color_type != "OBJECT":
             space.shading.color_type = "OBJECT"
        elif space.shading.type != "SOLID":
             # Force solid view if not already solid? Or just enable color?
             # Forcing solid might be intrusive. Let's just ensure object color if solid.
             pass


    except Exception as e:
        print(f"Error configuring viewport: {e}")


def restore_viewport_settings():
    """Restore original viewport shading settings."""
    global _original_shading_settings
    try:
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    for space in area.spaces:
                        if space.type == "VIEW_3D" and hasattr(space, "shading"):
                            space_id = getattr(space.v3d, "id_data", None)
                            if space_id and space_id in _original_shading_settings:
                                original = _original_shading_settings[space_id]
                                space.shading.type = original["type"]
                                space.shading.color_type = original["color_type"]
                                print(f"Restored viewport settings for space {space_id}") # Debug
        _original_shading_settings.clear() # Clear stored settings
    except Exception as e:
        print(f"Error restoring viewport settings: {e}")


# --- Timer Logic ---
_timer_interval = 5.0 # Check every 5 seconds

def update_timer_callback():
    """Function called periodically by Blender's timer."""
    if update_all_export_statuses():
         # Redraw areas if statuses changed
         for window in bpy.context.window_manager.windows:
             for area in window.screen.areas:
                 area.tag_redraw()
    return _timer_interval # Reschedule timer

# --- Optional Operators (Keep if needed for UI) ---
class MESH_OT_clear_all_indicators(Operator):
    """Clears export indicators from all mesh objects"""
    bl_idname = "mesh.clear_export_indicators"
    bl_label = "Clear All Export Indicators"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        count = 0
        for obj in bpy.data.objects:
            if obj.type == "MESH" and EXPORT_TIME_PROP in obj:
                restore_object_color(obj) # Restore color first
                cleanup_export_props(obj) # Then remove props
                count += 1
        self.report({"INFO"}, f"Cleared export indicators from {count} objects.")
        # Trigger redraw after clearing
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        return {"FINISHED"}

# --- Registration ---
operators_to_register = (
    MESH_OT_clear_all_indicators,
    # Add other indicator-specific operators here
)


def register():
    for cls in operators_to_register:
        try:
            bpy.utils.register_class(cls)
        except ValueError: # Catch if already registered during reload
            pass

    # Register timer only if it's not already registered
    if not bpy.app.timers.is_registered(update_timer_callback):
         configure_viewport_for_object_colors() # Configure viewport when timer starts
         bpy.app.timers.register(update_timer_callback, first_interval=_timer_interval)
         print("Export indicator timer registered.")


def unregister():
    # Unregister timer if it is registered
    if bpy.app.timers.is_registered(update_timer_callback):
         bpy.app.timers.unregister(update_timer_callback)
         print("Export indicator timer unregistered.")

    # Restore viewport settings when add-on is disabled
    restore_viewport_settings()

    # Restore all object colors and cleanup props on unregister
    for obj in bpy.data.objects:
         if obj.type == "MESH":
             # Check if props exist before trying to remove/restore
             if ORIGINAL_COLOR_PROP in obj:
                  restore_object_color(obj)
             if EXPORT_TIME_PROP in obj:
                  cleanup_export_props(obj)

    for cls in reversed(operators_to_register):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError: # Catch if already unregistered during reload
            pass