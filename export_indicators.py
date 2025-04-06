# export_indicators.py
"""Handles visual indicators for recently exported objects."""

import bpy
import time
import logging
from enum import Enum
from bpy.types import Operator

# --- Setup Logger ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(name)s:%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Default level

# --- Constants ---

class ExportStatus(Enum):
    """Enum to represent the export status based on time."""
    FRESH = 0   # Just exported (green) - less than FRESH_DURATION
    STALE = 1   # Exported a while ago (yellow) - less than STALE_DURATION
    NONE = 2    # No indicator needed / Expired


# Timing constants (in seconds)
FRESH_DURATION = 60    # 1 minute
STALE_DURATION = 300   # 5 minutes

# Custom property names (shared with operators.py)
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"
ORIGINAL_COLOR_PROP = "original_object_color" # For visual indicator

# Export status colors (RGBA)
STATUS_COLORS = {
    ExportStatus.FRESH.value: (0.2, 0.8, 0.2, 1.0),  # Green
    ExportStatus.STALE.value: (0.8, 0.8, 0.2, 1.0),  # Yellow
}

# Store original viewport settings per 3D view space ID
_original_shading_settings = {}


# --- Core Functions ---

def update_all_export_statuses():
    """Update status of all tracked objects based on elapsed time."""
    current_time = time.time()
    needs_redraw = False

    for obj in bpy.data.objects:
        if not (obj.type == "MESH" and EXPORT_TIME_PROP in obj):
            continue

        export_time = obj.get(EXPORT_TIME_PROP, 0)
        if not export_time:
            continue

        elapsed_time = current_time - export_time
        old_status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)

        # Determine new status
        if elapsed_time < FRESH_DURATION:
            new_status = ExportStatus.FRESH.value
        elif elapsed_time < STALE_DURATION:
            new_status = ExportStatus.STALE.value
        else:
            new_status = ExportStatus.NONE.value

        # Update object only if status has changed
        if new_status != old_status:
            obj[EXPORT_STATUS_PROP] = new_status
            set_object_color(obj)
            needs_redraw = True
            logger.debug(
                f"Updated status for {obj.name} to {ExportStatus(new_status).name}"
            )

            if new_status == ExportStatus.NONE.value:
                cleanup_export_props(obj)
                logger.debug(f"Cleaned up export props for {obj.name}")

    return needs_redraw


def get_recently_exported_objects():
    """Get a list of recently exported objects sorted by export time."""
    exported_objects = []
    for obj in bpy.data.objects:
        if obj.type == "MESH" and EXPORT_TIME_PROP in obj:
            status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
            if status != ExportStatus.NONE.value:
                exported_objects.append((obj, obj[EXPORT_TIME_PROP]))

    return sorted(exported_objects, key=lambda item: item[1], reverse=True)


def set_object_color(obj):
    """Set object viewport color based on its export status."""
    if not obj or EXPORT_STATUS_PROP not in obj:
        return

    status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)

    if (ORIGINAL_COLOR_PROP not in obj and
            status != ExportStatus.NONE.value):
        try:
            # Store copy of color tuple
            obj[ORIGINAL_COLOR_PROP] = list(obj.color)
        except AttributeError:
            logger.warning(
                f"Could not store original color for {obj.name}. "
                f"Color restore might fail."
            )
            # Ensure prop exists even if storing failed, to trigger restore logic
            if ORIGINAL_COLOR_PROP not in obj:
                 obj[ORIGINAL_COLOR_PROP] = list(obj.color) # Store default?


    if status in STATUS_COLORS:
        try:
            obj.color = STATUS_COLORS[status]
            obj.show_instancer_for_viewport = True # Required for object color
        except AttributeError as e:
             logger.error(f"Failed to set color for {obj.name}: {e}")
    else:
        restore_object_color(obj)


def restore_object_color(obj):
    """Restore object's original viewport color."""
    if not obj or ORIGINAL_COLOR_PROP not in obj:
        return

    try:
        original_color_list = obj[ORIGINAL_COLOR_PROP]
        if (isinstance(original_color_list, (list, tuple)) and
                len(original_color_list) == 4):
             obj.color = tuple(original_color_list)
        else:
             logger.warning(
                 f"Invalid original color stored for {obj.name}: "
                 f"{original_color_list}"
             )
        del obj[ORIGINAL_COLOR_PROP]
    except (ReferenceError, KeyError):
        pass
    except AttributeError as e:
        logger.error(f"Failed to restore color for {obj.name}: {e}")


def cleanup_export_props(obj):
    """Remove export tracking properties when status expires."""
    if not obj:
        return
    props_to_remove = [EXPORT_TIME_PROP, EXPORT_STATUS_PROP, ORIGINAL_COLOR_PROP]
    for prop in props_to_remove:
        if prop in obj:
            try:
                del obj[prop]
            except (ReferenceError, KeyError):
                pass


def configure_viewport_for_object_colors():
    """Configure active 3D viewport to display object colors in Solid mode."""
    global _original_shading_settings
    try:
        context = bpy.context
        area = next((a for a in context.screen.areas if a.type == "VIEW_3D"), None)
        if not area:
            logger.warning("Could not find active 3D Viewport area.")
            return
        space = next((s for s in area.spaces if s.type == "VIEW_3D"), None)
        if not space or not hasattr(space, "shading"):
            logger.warning("Could not find valid 3D Viewport space data.")
            return

        space_key = space.as_pointer()

        if space_key not in _original_shading_settings:
            _original_shading_settings[space_key] = {
                "type": space.shading.type,
                "color_type": space.shading.color_type
            }
            logger.debug("Stored original viewport settings for space.")

        if space.shading.type == "SOLID" and space.shading.color_type != "OBJECT":
            space.shading.color_type = "OBJECT"
            logger.info("Set 3D Viewport shading color type to 'Object'.")

    except Exception as e:
        logger.error(f"Error configuring viewport: {e}", exc_info=True)


def restore_viewport_settings():
    """Restore original viewport shading settings for all tracked viewports."""
    global _original_shading_settings
    restored_count = 0
    try:
        # Handle shutdown state
        if not bpy.data or not bpy.data.window_managers: return 

        for window in bpy.data.window_managers[0].windows:
            for screen in bpy.data.screens:
                for area in screen.areas:
                    if area.type == "VIEW_3D":
                        for space in area.spaces:
                            if space.type == "VIEW_3D" and hasattr(space, "shading"):
                                space_key = space.as_pointer()
                                if space_key in _original_shading_settings:
                                    original = _original_shading_settings[space_key]
                                    try:
                                        if (space.shading.type != original["type"] or
                                           space.shading.color_type != original["color_type"]):

                                            space.shading.type = original["type"]
                                            space.shading.color_type = original["color_type"]
                                            logger.debug(
                                                f"Restored viewport space settings to "
                                                f"{original['type']}/{original['color_type']}"
                                            )
                                            restored_count += 1
                                    except Exception as e:
                                         logger.warning(
                                             f"Failed restoring specific space setting: {e}"
                                         )
                                    # Remove entry once processed, prevents errors if space reused
                                    del _original_shading_settings[space_key]

    except Exception as e:
        logger.error(f"Error during viewport setting restoration: {e}")
    finally:
        if restored_count > 0:
             logger.info(f"Restored {restored_count} viewport shading settings.")
        _original_shading_settings.clear()


# --- Timer Logic ---
_timer_interval = 5.0

def update_timer_callback():
    """Function called periodically by Blender's timer."""
    try:
        if update_all_export_statuses():
            if bpy.context.window_manager:
                 for window in bpy.context.window_manager.windows:
                     for area in window.screen.areas:
                         if area.type == "VIEW_3D":
                             for region in area.regions:
                                 if region.type == "UI":
                                     region.tag_redraw()
                                     break # Only need one UI region redraw
    except Exception as e:
         logger.error(f"Error in timer callback: {e}", exc_info=True)
         # Consider returning None to stop the timer if errors persist
    return _timer_interval


# --- Operators ---

class MESH_OT_clear_all_indicators(Operator):
    """Clears export indicators from all mesh objects."""
    bl_idname = "mesh.clear_export_indicators"
    bl_label = "Clear All Export Indicators"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Runs the clear operation."""
        count = 0
        for obj in bpy.data.objects:
            if obj.type == "MESH" and EXPORT_TIME_PROP in obj:
                restore_object_color(obj)
                cleanup_export_props(obj)
                count += 1
        msg = f"Cleared export indicators from {count} objects."
        self.report({"INFO"}, msg)
        logger.info(msg)

        if context.window_manager:
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
        return {"FINISHED"}


# --- Registration ---

operators_to_register = (
    MESH_OT_clear_all_indicators,
)


def register():
    """Registers classes and starts the timer."""
    for cls in operators_to_register:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            logger.warning(f"Class {cls.__name__} already registered.")
            pass

    if not bpy.app.timers.is_registered(update_timer_callback):
        try:
            configure_viewport_for_object_colors()
            bpy.app.timers.register(
                update_timer_callback, first_interval=_timer_interval
            )
            logger.info("Export indicator timer registered.")
        except Exception as e:
             logger.error(f"Failed to register timer: {e}", exc_info=True)


def unregister():
    """Unregisters classes, stops timer, restores viewport & objects."""
    logger.info("Unregistering export indicators...")
    if bpy.app.timers.is_registered(update_timer_callback):
        try:
            bpy.app.timers.unregister(update_timer_callback)
            logger.info("Export indicator timer unregistered.")
        except Exception as e:
            logger.error(f"Failed to unregister timer: {e}")

    try:
        restore_viewport_settings()
    except Exception as e:
        logger.error(f"Failed to restore viewport settings: {e}")

    try:
        count_cleaned = 0
        # Check if bpy.data exists (might be None during final shutdown)
        if bpy.data:
            for obj in bpy.data.objects:
                if obj.type == "MESH":
                    props_found = False
                    if ORIGINAL_COLOR_PROP in obj:
                        restore_object_color(obj)
                        props_found = True
                    # cleanup_export_props handles multiple props
                    if EXPORT_TIME_PROP in obj:
                        cleanup_export_props(obj)
                        props_found = True
                    if props_found:
                        count_cleaned += 1
        if count_cleaned > 0:
            logger.info(f"Cleaned up props/color for {count_cleaned} objects.")
    except Exception as e:
        logger.error(f"Error during object property cleanup: {e}")

    for cls in reversed(operators_to_register):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
             logger.warning(f"Class {cls.__name__} already unregistered.")
             pass