# export_indicators.py
"""
Handles visual indicators (object colour changes) for recently 
exported objects.

Relies on custom properties set by the main export operator:
- mesh_export_timestamp: Time of export.
- mesh_export_status: Current status (FRESH, STALE, NONE).

Requires the user to set their 3D Viewport shading colour 
type to 'Object' in Solid display mode to see the colour changes.
"""

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
    logger.setLevel(logging.INFO)  # Default level

# --- Constants ---

class ExportStatus(Enum):
    """Enum to represent the export status based on time."""
    FRESH = 0   # Just exported (green)
    STALE = 1   # Exported a while ago (yellow)
    NONE = 2    # No indicator needed / Expired


# Timing constants (in seconds)
FRESH_DURATION_SECONDS = 60     # 1 minute
STALE_DURATION_SECONDS = 300    # 5 minutes
# FRESH_DURATION_SECONDS = 5     # debug
# STALE_DURATION_SECONDS = 10    # debug


# Custom property names
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"
ORIGINAL_COLOUR_PROP = "mesh_exporter_original_colour"

# Export status colours (RGBA tuple)
STATUS_COLOURS = {
    ExportStatus.FRESH.value: (0.2, 0.8, 0.2, 1.0),  # Green
    ExportStatus.STALE.value: (0.8, 0.8, 0.2, 1.0),  # Yellow
}

# Timer interval
_TIMER_INTERVAL_SECONDS = 5.0


# --- Core Functions ---


def mark_object_as_exported(obj):
    """
    Mark an object as just exported by setting custom properties.
    This is used to track the export status of objects.
    
    Args:
        obj (bpy.types.Object): The object to mark as exported.
    
    Returns:
        None
    """
    if obj is None or obj.type != "MESH":
        return
        
    # Ensure timer is registered
    if not bpy.app.timers.is_registered(update_timer_callback):
        logger.warning("Export indicators timer not registered - "
                       "registering now")
        try:
            bpy.app.timers.register(
                update_timer_callback,
                first_interval=_TIMER_INTERVAL_SECONDS,
                persistent=True
            )
        except Exception as e:
            logger.error(f"Failed to register timer in "
                         f"mark_object_as_exported: {e}")
    
    # Mark the object
    obj[EXPORT_TIME_PROP] = time.time()
    obj[EXPORT_STATUS_PROP] = ExportStatus.FRESH.value
    set_object_colour(obj)
    logger.info(f"Marked {obj.name} as freshly exported")

def _delete_prop(obj, prop_name):
    """
    Safely delete a custom property from an object if it exists.

    Args:
        obj (bpy.types.Object): The object to modify.
        prop_name (str): The name of the property to delete.

    Returns:
        bool: True if the property was deleted or didn't exist, False on error.
    """
    if not obj or not hasattr(obj, "name"):
        logger.debug(f"Cannot delete prop {prop_name}, object invalid.")
        return False
    if obj.get(prop_name) is None:
        return True # Property doesn't exist, consider it "deleted"

    try:
        del obj[prop_name]
        logger.debug(f"Deleted prop {prop_name} for {obj.name}")
        return True
    except (ReferenceError, KeyError):
        logger.debug(f"Prop {prop_name} already gone/obj "
                     f"invalid for {obj.name}.")
        # Consider it deleted if it's gone
        return True
    except Exception as e:
        logger.warning(f"Error removing prop {prop_name} from {obj.name}: {e}")
    return False


def restore_object_colour(obj):
    """
    Restore object's original viewport colour if stored previously.
    Also ensures the original colour property is removed.

    Args:
        obj (bpy.types.Object): The object whose colour to restore.

    Returns:
        bool: True if colour was restored or not needed, False on failure.
    """
    if not obj or not hasattr(obj, "name"):
        logger.debug("Skipping restore: object invalid.")
        return False
    if ORIGINAL_COLOUR_PROP not in obj:
        logger.debug(f"No original colour stored for {obj.name}, "
                     f"skipping restore.")
        return True # Nothing needed to restore

    logger.debug(f"Attempting to restore colour for {obj.name}...")
    original_colour_stored = None
    restore_success = False

    try:
        original_colour_stored = obj[ORIGINAL_COLOUR_PROP]
        log_type = type(original_colour_stored)
        logger.debug(f"Retrieved stored colour prop for {obj.name}: "
                     f"{original_colour_stored} (Type: {log_type})")

        # Check if it behaves like a sequence of length 4
        is_valid_sequence = False
        if hasattr(original_colour_stored, '__len__') and \
           hasattr(original_colour_stored, '__getitem__'):
            try:
                if len(original_colour_stored) == 4:
                    is_valid_sequence = True
            except Exception as e:
                logger.warning(f"Error checking len/getitem for stored colour "
                               f"on {obj.name}: {e}")

        if is_valid_sequence:
            try:
                original_colour_tuple = tuple(
                    float(c) for c in original_colour_stored
                )
                current_colour_tuple = tuple(float(c) for c in obj.color)

                if current_colour_tuple != original_colour_tuple:
                    obj.color = original_colour_tuple
                    logger.info(
                        f"Restored colour for {obj.name} to "
                        f"{original_colour_tuple}"
                    )
                else:
                    logger.debug(f"Colour for {obj.name} already "
                                 f"matches original.")
                restore_success = True

            except (AttributeError, TypeError, ValueError) as e:
                 logger.error(
                     f"Failed to apply stored colour {original_colour_stored} "
                     f"for {obj.name}: {e}"
                  )
            except ReferenceError:
                 logger.warning(f"Object {obj.name} became invalid "
                                f"during colour apply.")

        else:
             logger.warning(
                 f"Invalid original colour data stored for {obj.name}: "
                 f"Not a sequence of length 4 "
                 f"(Value: {original_colour_stored}, Type: {log_type}). "
                 f"Cannot restore."
             )

    except KeyError:
        logger.debug(f"Original colour prop key missing for {obj.name}.")
        restore_success = True # Prop gone, consider restore "successful"
    except ReferenceError:
        logger.warning(f"Object {obj.name} became invalid during "
                       f"restore read.")
    except Exception as e:
         logger.error(f"Unexpected error restoring colour for {obj.name}: {e}")

    # Always ensure the original colour prop 
    # is removed after attempting restore.
    logger.debug(f"Ensuring cleanup of original colour prop for {obj.name}")
    _delete_prop(obj, ORIGINAL_COLOUR_PROP)

    return restore_success


def set_object_colour(obj):
    """
    Set object viewport colour based on its current export status.
    Stores the original colour if setting an indicator colour 
    for the first time.

    Args:
        obj (bpy.types.Object): The object whose colour to set.
    """
    if not obj or not hasattr(obj, "name"):
        logger.debug("Skipping set_object_colour: object invalid.")
        return
    if EXPORT_STATUS_PROP not in obj:
        logger.debug(f"Skipping set_object_colour for {obj.name}: "
                     f"No status prop.")
        return

    try:
        status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
        target_colour = STATUS_COLOURS.get(status)

        if not target_colour:
            logger.debug(f"No target colour for {obj.name} (status={status}).")
            return

        # --- Store Original Colour (If Needed) ---
        if ORIGINAL_COLOUR_PROP not in obj:
            try:
                current_colour_prop = obj.color
                logger.debug(f"Reading obj.color for {obj.name}: "
                             f"{current_colour_prop} "
                             f"(Type: {type(current_colour_prop)})")

                # Store as list of floats
                original_colour_list = [float(c) for c in current_colour_prop]

                if len(original_colour_list) == 4:
                    obj[ORIGINAL_COLOUR_PROP] = original_colour_list
                    logger.debug(f"Stored original colour for {obj.name} "
                                 f"as list: {original_colour_list}")
                else:
                     logger.warning(
                         f"Could not store original colour for {obj.name}: "
                         f"obj.color returned unexpected length: "
                         f"{current_colour_prop}"
                     )
            except (AttributeError, TypeError, 
                    ValueError, ReferenceError) as e:
                logger.warning(
                    f"Could not read or store original colour for {obj.name}: "
                    f"{e}. Restore may fail."
                )

        # --- Apply Status Colour ---
        try:
            current_colour_tuple = tuple(float(c) for c in obj.color)
            if current_colour_tuple != target_colour:
                obj.color = target_colour
                logger.debug(f"Set colour for {obj.name} to {target_colour}")
            # Property exists since Blender 2.8 according to docs
            if hasattr(obj, 'show_instancer_for_viewport'):
                obj.show_instancer_for_viewport = True
        except (AttributeError, TypeError, ValueError, ReferenceError) as e:
             logger.error(f"Failed to set status colour/property "
                          f"for {obj.name}: {e}")

    except ReferenceError:
         logger.debug(f"Object {obj.name} became invalid "
                      f"during set_object_colour.")
    except Exception as e:
        logger.error(f"Unexpected error in set_object_colour "
                     f"for {obj.name}: {e}")


def update_all_export_statuses():
    """
    Iterate through objects, update export status based on elapsed time.
    Returns True if any object's status changed, indicating a redraw is needed.
    """
    current_time = time.time()
    needs_redraw = False
    status_changes = []

    if not bpy.data or not bpy.data.objects:
        logger.debug("No objects found to update statuses")
        return False

    # Iterate safely over object list copy
    for obj in list(bpy.data.objects):
        try:
            if not (obj and obj.type == "MESH" and EXPORT_TIME_PROP in obj):
                continue

            export_time = obj.get(EXPORT_TIME_PROP, 0)
            if not export_time:
                logger.warning(f"Object {obj.name} missing timestamp prop.")
                continue

            elapsed_time = current_time - export_time
            old_status_val = obj.get(EXPORT_STATUS_PROP, 
                                     ExportStatus.NONE.value)
            old_status_name = (ExportStatus(old_status_val).name 
                               if isinstance(old_status_val, int) 
                               else "UNKNOWN")

            new_status = ExportStatus.NONE
            if elapsed_time < FRESH_DURATION_SECONDS:
                new_status = ExportStatus.FRESH
            elif elapsed_time < STALE_DURATION_SECONDS:
                new_status = ExportStatus.STALE

            new_status_val = new_status.value
            
            # Only log when there's a status change
            if new_status_val != old_status_val:
                status_changes.append((obj.name, old_status_name, 
                                       new_status.name, elapsed_time))
                needs_redraw = True
                
                # State transition logic
                if new_status == ExportStatus.NONE:
                    # Restores colour, removes original prop
                    restore_object_colour(obj)
                    # Remove remaining tracking props
                    _delete_prop(obj, EXPORT_TIME_PROP)
                    _delete_prop(obj, EXPORT_STATUS_PROP)
                else:
                    # Becoming FRESH or STALE: Set new status prop, then colour
                    obj[EXPORT_STATUS_PROP] = new_status_val
                    set_object_colour(obj)

        except ReferenceError:
            logger.debug("Object became invalid during status update loop.")
            continue
        except Exception as e:
            obj_name = obj.name if obj and hasattr(obj, 'name') else 'N/A'
            logger.error(f"Error updating status for object {obj_name}: {e}")
            continue
    
    # Log status changes together for easier debugging
    if status_changes:
        logger.info(f"Status changes detected: {len(status_changes)} "
                    f"objects updated")
        for change in status_changes:
            name, old, new, elapsed = change
            logger.info(f"  → {name}: {old} → {new} (elapsed: {elapsed:.1f}s)")
    
    return needs_redraw


def get_recently_exported_objects():
    """Get a list of objects with active FRESH/STALE status, sorted."""
    exported_objects = []
    if not bpy.data or not bpy.data.objects:
        return []

    for obj in bpy.data.objects:
        try:
            if (obj and obj.type == "MESH" and EXPORT_TIME_PROP in obj):
                status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
                if status != ExportStatus.NONE.value:
                    timestamp = obj.get(EXPORT_TIME_PROP, 0)
                    exported_objects.append((obj, timestamp))
        except ReferenceError:
             continue # Object invalid

    return sorted(exported_objects, key=lambda item: item[1], reverse=True)


# --- Timer Logic ---

def update_timer_callback():
    """Function called periodically by Blender's timer."""
    try:
        current_time = time.time()
        logger.debug(f"[MESH_EXPORTER] Timer tick at {current_time}")
        
        status_updated = update_all_export_statuses()
        
        if status_updated:
            # More aggressive UI updating
            context = bpy.context
            if (context 
                and hasattr(context, "window_manager") 
                and context.window_manager):
                for window in context.window_manager.windows:
                    if not hasattr(window, "screen") or not window.screen:
                        continue
                    for area in window.screen.areas:
                        try:
                            # Force update for all area types
                            area.tag_redraw()
                        except Exception as e:
                            # Log potential errors during redraw 
                            # without stopping timer
                            logger.debug(f"Error redrawing area "
                                         f"{area.type}: {e}")
                            pass
            else:
                logger.warning("Timer callback couldn't redraw: "
                               "invalid context")
    except Exception as e:
        # Log but don't stop the timer
        logger.error(f"[MESH_EXPORTER] Timer error: {e}", exc_info=True)
    
    # Always return the interval to keep the timer running
    return _TIMER_INTERVAL_SECONDS


# --- Operators ---

class MESH_OT_clear_all_indicators(Operator):
    """Clears export indicators from all mesh objects."""
    bl_idname = "mesh.clear_export_indicators"
    bl_label = "Clear All Export Indicators"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Runs the clear operation."""
        count = 0
        if not bpy.data or not bpy.data.objects:
            logger.warning("Clear Indicators: No Blender data found.")
            return {'CANCELLED'}

        logger.info("Clearing all export indicators...")
        # Iterate over list copy for safety
        for obj in list(bpy.data.objects):
            if obj and obj.type == "MESH" and \
               (EXPORT_TIME_PROP in obj or ORIGINAL_COLOUR_PROP in obj):
                obj_name = obj.name
                try:
                    # Handles original colour prop removal
                    restore_object_colour(obj) 
                    _delete_prop(obj, EXPORT_TIME_PROP)
                    _delete_prop(obj, EXPORT_STATUS_PROP)
                    count += 1
                except Exception as e:
                    logger.warning(f"Error clearing indicators "
                                   f"for {obj_name}: {e}")

        msg = f"Cleared export indicators from {count} objects."
        self.report({"INFO"}, msg)
        logger.info(msg)

        # Trigger redraw after clearing
        if context and context.window_manager:
            for window in context.window_manager.windows:
                if not window.screen: 
                    continue
                for area in window.screen.areas:
                    try:
                        area.tag_redraw()
                    except ReferenceError: 
                        pass # Area might close
        return {"FINISHED"}
    

class MESH_OT_debug_update_indicators(Operator):
    """Forces an immediate update of all export indicators."""
    bl_idname = "mesh.debug_update_indicators"
    bl_label = "Update Export Indicators"
    bl_options = {"REGISTER"}

    def execute(self, context):
        """Runs the update operation."""
        status_changed = update_all_export_statuses()
        
        msg = f"Export indicators updated. Status changed: {status_changed}"
        self.report({"INFO"}, msg)
        logger.info(msg)
        
        # Force redraw
        for window in context.window_manager.windows:
            if window.screen:
                for area in window.screen.areas:
                    area.tag_redraw()
                    
        return {"FINISHED"}


# --- Registration ---

operators_to_register = (
    MESH_OT_clear_all_indicators,
    MESH_OT_debug_update_indicators,
)


def register():
    """Registers classes and starts the timer."""
    logger.debug("Registering export indicator classes...")
    for cls in operators_to_register:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            logger.debug(f"Class {cls.__name__} already registered.")
            pass

    # Always unregister first to prevent duplicate timers
    if bpy.app.timers.is_registered(update_timer_callback):
        try:
            bpy.app.timers.unregister(update_timer_callback)
            logger.debug("Unregistered existing timer before re-registering")
        except Exception as e:
            logger.warning(f"Failed to unregister existing timer: {e}")

    # Now register a fresh timer with persistence
    try:
        bpy.app.timers.register(
            update_timer_callback,
            first_interval=_TIMER_INTERVAL_SECONDS,
            persistent=True  # Make timer survive file loads
        )
        logger.info(f"Export indicator timer registered (interval: "
                    f"{_TIMER_INTERVAL_SECONDS}s, persistent)")
    except Exception as e:
        logger.error(f"Failed to register timer: {e}", exc_info=True)


def unregister():
    """Unregisters classes, stops timer, and cleans up objects."""
    logger.info("Unregistering export indicators...")
    # Stop and unregister timer
    if bpy.app.timers.is_registered(update_timer_callback):
        try:
            bpy.app.timers.unregister(update_timer_callback)
            logger.info("Export indicator timer unregistered.")
        except Exception as e:
            logger.error(f"Failed to unregister timer: {e}")

    # No longer restoring viewport settings automatically

    # Cleanup object properties and colours
    try:
        count_cleaned = 0
        if bpy.data and bpy.data.objects:
            for obj in list(bpy.data.objects): # Use list copy
                if obj and obj.type == "MESH" and \
                   (EXPORT_TIME_PROP in obj or ORIGINAL_COLOUR_PROP in obj):
                    obj_name = obj.name
                    try:
                        restore_object_colour(obj)
                        _delete_prop(obj, EXPORT_TIME_PROP)
                        _delete_prop(obj, EXPORT_STATUS_PROP)
                        count_cleaned += 1
                    except Exception as inner_e:
                        logger.warning(f"Error cleaning up {obj_name}: "
                                       f"{inner_e}")
            if count_cleaned > 0:
                logger.info(f"Cleaned up indicators for "
                            f"{count_cleaned} objects.")
    except Exception as e:
        logger.error(f"Error during object property cleanup: {e}")

    # Unregister operators
    for cls in reversed(operators_to_register):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
             logger.debug(f"Class {cls.__name__} already unregistered.")
             pass
    logger.debug("Export indicator unregistration finished.")