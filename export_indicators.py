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
from enum import Enum
from bpy.types import Operator

# --- Constants ---


class ExportStatus(Enum):
    """Enum to represent the export status based on time."""

    FRESH = 0  # Just exported (green)
    STALE = 1  # Exported a while ago (yellow)
    NONE = 2  # No indicator needed / Expired


# Timing constants (in seconds)
FRESH_DURATION_SECONDS = 60  # 1 minute
STALE_DURATION_SECONDS = 300  # 5 minutes
# FRESH_DURATION_SECONDS = 5     # debug
# STALE_DURATION_SECONDS = 10    # debug


# Custom property names
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"
ORIGINAL_COLOUR_PROP = "mesh_exporter_original_colour"

# Caching for performance optimization
_exported_objects_cache = []
_cache_last_update = 0
_cache_update_interval = 10.0  # Update cache every 10 seconds

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

    # Check if export indicators are enabled in scene properties
    scene = bpy.context.scene
    if hasattr(scene, "mesh_exporter") and scene.mesh_exporter:
        if not scene.mesh_exporter.mesh_export_show_indicators:
            return

    # Ensure timer is registered
    if not bpy.app.timers.is_registered(update_timer_callback):
        try:
            bpy.app.timers.register(
                update_timer_callback,
                first_interval=_TIMER_INTERVAL_SECONDS,
                persistent=True,
            )
        except (RuntimeError, ValueError):
            pass

    # Mark the object
    obj[EXPORT_TIME_PROP] = time.time()
    obj[EXPORT_STATUS_PROP] = ExportStatus.FRESH.value
    set_object_colour(obj)

    # Invalidate cache since we added a new exported object
    global _cache_last_update
    _cache_last_update = 0


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
        return False
    if obj.get(prop_name) is None:
        return True  # Property doesn't exist, consider it "deleted"

    try:
        del obj[prop_name]
        return True
    except (ReferenceError, KeyError):
        # Consider it deleted if it's gone
        return True
    except TypeError:
        pass
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
        return False
    if ORIGINAL_COLOUR_PROP not in obj:
        return True  # Nothing needed to restore

    original_colour_stored = None
    restore_success = False

    try:
        original_colour_stored = obj[ORIGINAL_COLOUR_PROP]

        # Check if it behaves like a sequence of length 4
        is_valid_sequence = False
        if hasattr(original_colour_stored, "__len__") and hasattr(
            original_colour_stored, "__getitem__"
        ):
            try:
                if len(original_colour_stored) == 4:
                    is_valid_sequence = True
            except TypeError:
                pass

        if is_valid_sequence:
            try:
                original_colour_tuple = tuple(float(c) for c in original_colour_stored)
                current_colour_tuple = tuple(float(c) for c in obj.color)

                if current_colour_tuple != original_colour_tuple:
                    obj.color = original_colour_tuple
                restore_success = True

            except (AttributeError, TypeError, ValueError):
                pass
            except ReferenceError:
                pass

        else:
            pass

    except KeyError:
        restore_success = True  # Prop gone, consider restore "successful"
    except ReferenceError:
        pass
    except (AttributeError, TypeError):
        pass

    # Always ensure the original colour prop
    # is removed after attempting restore.
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
        return
    if EXPORT_STATUS_PROP not in obj:
        return

    try:
        status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
        target_colour = STATUS_COLOURS.get(status)

        if not target_colour:
            return

        # --- Store Original Colour (If Needed) ---
        if ORIGINAL_COLOUR_PROP not in obj:
            try:
                current_colour_prop = obj.color

                # Store as list of floats
                original_colour_list = [float(c) for c in current_colour_prop]

                if len(original_colour_list) == 4:
                    obj[ORIGINAL_COLOUR_PROP] = original_colour_list
                else:
                    pass
            except (AttributeError, TypeError, ValueError, ReferenceError):
                pass

        # --- Apply Status Colour ---
        try:
            current_colour_tuple = tuple(float(c) for c in obj.color)
            if current_colour_tuple != target_colour:
                obj.color = target_colour
            # Property exists since Blender 2.8 according to docs
            if hasattr(obj, "show_instancer_for_viewport"):
                obj.show_instancer_for_viewport = True
        except (AttributeError, TypeError, ValueError, ReferenceError):
            pass

    except ReferenceError:
        pass
    except (AttributeError, TypeError, KeyError):
        pass


def _get_cached_exported_objects():
    """Get cached list of objects with export properties.

    Returns:
        list: List of valid mesh objects with export properties
    """
    global _exported_objects_cache, _cache_last_update
    current_time = time.time()

    # Update cache if it's stale
    if (current_time - _cache_last_update) >= _cache_update_interval:
        valid_objects = []
        for obj in bpy.data.objects:
            try:
                # Verify object is still valid by accessing a property
                if obj and obj.type == "MESH" and EXPORT_TIME_PROP in obj:
                    valid_objects.append(obj)
            except ReferenceError:
                # Object was deleted, skip it
                continue

        _exported_objects_cache = valid_objects
        _cache_last_update = current_time

    # Filter out any invalid references that may have appeared since last update
    return [obj for obj in _exported_objects_cache if _is_valid_object(obj)]


def _is_valid_object(obj):
    """Check if an object reference is still valid.

    Args:
        obj: The object to check

    Returns:
        bool: True if object is valid, False otherwise
    """
    if not obj:
        return False
    try:
        # Access a property to trigger ReferenceError if object was deleted
        _ = obj.type
        return True
    except ReferenceError:
        return False


def update_all_export_statuses():
    """
    Iterate through objects, update export status based on elapsed time.
    Returns True if any object's status changed, indicating a redraw is needed.
    """
    current_time = time.time()
    needs_redraw = False
    status_changes = []

    if not bpy.data or not bpy.data.objects:
        return False

    # Use cached list of exported objects for better performance
    exported_objects = _get_cached_exported_objects()

    # Iterate over cached exported objects only
    for obj in exported_objects:
        try:
            if not (obj and obj.type == "MESH" and EXPORT_TIME_PROP in obj):
                continue

            export_time = obj.get(EXPORT_TIME_PROP, 0)
            if not export_time:
                continue

            elapsed_time = current_time - export_time
            old_status_val = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
            old_status_name = (
                ExportStatus(old_status_val).name
                if isinstance(old_status_val, int)
                else "UNKNOWN"
            )

            new_status = ExportStatus.NONE
            if elapsed_time < FRESH_DURATION_SECONDS:
                new_status = ExportStatus.FRESH
            elif elapsed_time < STALE_DURATION_SECONDS:
                new_status = ExportStatus.STALE

            new_status_val = new_status.value

            # Only act when there's a status change
            if new_status_val != old_status_val:
                status_changes.append(
                    (obj.name, old_status_name, new_status.name, elapsed_time)
                )
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
            continue
        except (AttributeError, TypeError, KeyError):
            continue

    return needs_redraw


def get_recently_exported_objects():
    """Get a list of objects with active FRESH/STALE status, sorted."""
    exported_objects = []
    if not bpy.data or not bpy.data.objects:
        return []

    for obj in bpy.data.objects:
        try:
            if obj and obj.type == "MESH" and EXPORT_TIME_PROP in obj:
                status = obj.get(EXPORT_STATUS_PROP, ExportStatus.NONE.value)
                if status != ExportStatus.NONE.value:
                    timestamp = obj.get(EXPORT_TIME_PROP, 0)
                    exported_objects.append((obj, timestamp))
        except ReferenceError:
            continue  # Object invalid

    return sorted(exported_objects, key=lambda item: item[1], reverse=True)


# --- Timer Logic ---


def update_timer_callback():
    """Function called periodically by Blender's timer."""
    try:
        # Check if indicators are enabled
        scene = bpy.context.scene
        if hasattr(scene, "mesh_exporter") and scene.mesh_exporter:
            if not scene.mesh_exporter.mesh_export_show_indicators:
                # Still return interval to keep timer registered
                return _TIMER_INTERVAL_SECONDS

        status_updated = update_all_export_statuses()

        if status_updated:
            # More aggressive UI updating
            context = bpy.context
            if (
                context
                and hasattr(context, "window_manager")
                and context.window_manager
            ):
                for window in context.window_manager.windows:
                    if not hasattr(window, "screen") or not window.screen:
                        continue
                    for area in window.screen.areas:
                        try:
                            # Force update for all area types
                            area.tag_redraw()
                        except (AttributeError, RuntimeError):
                            # Ignore potential errors during redraw
                            # without stopping timer
                            pass
            else:
                pass
    except (ReferenceError, RuntimeError, AttributeError):
        # Ignore but don't stop the timer
        pass

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
            return {"CANCELLED"}

        # Iterate over list copy for safety
        for obj in list(bpy.data.objects):
            if (
                obj
                and obj.type == "MESH"
                and (EXPORT_TIME_PROP in obj or ORIGINAL_COLOUR_PROP in obj)
            ):
                try:
                    # Handles original colour prop removal
                    restore_object_colour(obj)
                    _delete_prop(obj, EXPORT_TIME_PROP)
                    _delete_prop(obj, EXPORT_STATUS_PROP)
                    count += 1
                except (ReferenceError, AttributeError, KeyError):
                    pass

        msg = f"Cleared export indicators from {count} objects."
        self.report({"INFO"}, msg)

        # Trigger redraw after clearing
        if context and context.window_manager:
            for window in context.window_manager.windows:
                if not window.screen:
                    continue
                for area in window.screen.areas:
                    try:
                        area.tag_redraw()
                    except ReferenceError:
                        pass  # Area might close
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
    for cls in operators_to_register:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass

    # Always unregister first to prevent duplicate timers
    if bpy.app.timers.is_registered(update_timer_callback):
        try:
            bpy.app.timers.unregister(update_timer_callback)
        except (ValueError, RuntimeError):
            pass

    # Now register a fresh timer with persistence
    try:
        bpy.app.timers.register(
            update_timer_callback,
            first_interval=_TIMER_INTERVAL_SECONDS,
            persistent=True,  # Make timer survive file loads
        )
    except (RuntimeError, ValueError):
        pass


def unregister():
    """Unregisters classes, stops timer, and cleans up objects."""
    # Stop and unregister timer
    if bpy.app.timers.is_registered(update_timer_callback):
        try:
            bpy.app.timers.unregister(update_timer_callback)
        except (ValueError, RuntimeError):
            pass

    # No longer restoring viewport settings automatically

    # Cleanup object properties and colours
    try:
        count_cleaned = 0
        if bpy.data and bpy.data.objects:
            for obj in list(bpy.data.objects):  # Use list copy
                if (
                    obj
                    and obj.type == "MESH"
                    and (EXPORT_TIME_PROP in obj or ORIGINAL_COLOUR_PROP in obj)
                ):
                    try:
                        restore_object_colour(obj)
                        _delete_prop(obj, EXPORT_TIME_PROP)
                        _delete_prop(obj, EXPORT_STATUS_PROP)
                        count_cleaned += 1
                    except (ReferenceError, AttributeError, KeyError):
                        pass
            if count_cleaned > 0:
                pass
    except (ReferenceError, AttributeError, RuntimeError):
        pass

    # Unregister operators
    for cls in reversed(operators_to_register):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
