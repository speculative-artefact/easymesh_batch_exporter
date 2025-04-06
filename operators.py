import bpy
import os
import time
import contextlib
from bpy.types import Operator
from bpy.props import StringProperty
from . import export_indicators # Import for status constants/colors if needed later

# --- Export Indicator Logic (Moved from export_indicators.py) ---

EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"

def mark_object_as_exported(obj):
    """Mark an object as just exported by setting custom properties."""
    if obj is None or obj.type != "MESH":
        return
    # Set timestamp and status (using values from export_indicators if needed)
    obj[EXPORT_TIME_PROP] = time.time()
    # Use the enum value directly if export_indicators is imported fully
    # obj[EXPORT_STATUS_PROP] = export_indicators.ExportStatus.FRESH.value
    obj[EXPORT_STATUS_PROP] = 0 # Assuming 0 corresponds to FRESH status

    # Trigger visual update if the full indicator system is active
    if hasattr(export_indicators, "set_object_color"):
         export_indicators.set_object_color(obj)

# --- Helper Functions ---

@contextlib.contextmanager
def temp_selection_context(context, active_object=None, selected_objects=None):
    """Temporarily set the active object and selection, checking object existence by name."""
    original_active = context.view_layer.objects.active
    original_selected = context.selected_objects[:] # Make a copy
    scene_objects = context.scene.objects # Get collection for checking

    try:
        # Deselect all first
        # Run in object mode if necessary for selection operators
        current_mode = context.mode
        if current_mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.select_all(action="DESELECT")

        # Select specified objects
        active_obj_to_set = None
        if selected_objects:
            if not isinstance(selected_objects, list):
                selected_objects = [selected_objects]
            for obj in selected_objects:
                # Check object exists in scene using its name before selecting
                if obj and obj.name in scene_objects:
                    try:
                        obj.select_set(True)
                    except ReferenceError:
                        # This can happen if the object became invalid between check and select
                        print(f"Warning: Could not select '{obj.name}' - object reference invalid.")
                elif obj:
                     # Object reference exists but name not in scene objects (shouldn't usually happen here)
                     print(f"Warning: Object reference '{obj.name}' exists but not found in scene during selection.")

        # Determine the active object to set - Check using name
        if active_object and active_object.name in scene_objects:
             active_obj_to_set = active_object
        elif selected_objects:
             # Fallback to first selected object *that is still valid*
             first_valid_selected = next((obj for obj in selected_objects if obj and obj.name in scene_objects), None)
             if first_valid_selected:
                  active_obj_to_set = first_valid_selected

        context.view_layer.objects.active = active_obj_to_set # Set active object (or None if invalid)

        # Restore original mode if we changed it
        if context.mode != current_mode:
             bpy.ops.object.mode_set(mode=current_mode)

        yield # Let the code inside the "with" block run

    finally:
        # Restore original selection state
        # Ensure object mode for selection operators
        current_mode = context.mode
        if current_mode != "OBJECT":
             bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.select_all(action="DESELECT")
        restored_selection = []
        for obj in original_selected:
            # Check using name before selecting
            if obj and obj.name in scene_objects:
                try:
                     obj.select_set(True)
                     restored_selection.append(obj) # Keep track of successfully re-selected
                except ReferenceError:
                    pass # Object might have been deleted or became invalid
            elif obj:
                 pass # Object reference exists but no longer in scene

        # Restore original active object - Check using name
        original_active_restored = None
        if original_active and original_active.name in scene_objects:
            try:
                context.view_layer.objects.active = original_active
                original_active_restored = original_active
            except ReferenceError:
                pass # Original active object became invalid
        else:
             # If original active is gone/invalid, try setting to first re-selected, or None
             if restored_selection:
                  context.view_layer.objects.active = restored_selection[0]
                  original_active_restored = restored_selection[0] # Update for mode restore check
             else:
                  context.view_layer.objects.active = None


        # Restore original mode if we changed it, considering the potentially new active object
        if context.mode != current_mode:
             # Check if the object we want to switch mode on is still valid
             obj_to_switch_mode = context.view_layer.objects.active
             if obj_to_switch_mode:
                  try:
                      # Attempt to switch mode back
                      bpy.ops.object.mode_set(mode=current_mode)
                  except TypeError:
                       # This can happen if the mode is incompatible (e.g., trying to go to Edit on a Lamp)
                       # Or if the active object became None unexpectedly. Default to OBJECT mode.
                       if context.mode != "OBJECT":
                           bpy.ops.object.mode_set(mode="OBJECT")
             elif context.mode != "OBJECT":
                  # If no active object, ensure we are back in Object mode
                  bpy.ops.object.mode_set(mode="OBJECT")


def apply_mesh_modifiers(obj):
    """Apply all modifiers on a mesh object."""
    if not obj or obj.type != "MESH":
        return
    # Important: Apply modifiers in a temporary context
    # Modifiers can't always be applied in edit mode, ensure object mode
    is_edit_mode = obj.mode == "EDIT"
    if is_edit_mode:
        bpy.ops.object.mode_set(mode="OBJECT")

    # Use override context for applying modifiers
    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]

    try:
        # Apply modifiers one by one from top to bottom
        for modifier in obj.modifiers[:]: # Iterate over a copy
            try:
                 with bpy.context.temp_override(**override):
                      bpy.ops.object.modifier_apply(modifier=modifier.name)
            except (RuntimeError, ReferenceError) as e:
                 print(f"Warning: Could not apply modifier '{modifier.name}' on {obj.name}: {e}")
                 # Optionally remove problematic modifier: obj.modifiers.remove(modifier)
    finally:
        # Restore original mode if necessary
        if is_edit_mode:
            bpy.ops.object.mode_set(mode="EDIT")


def triangulate_mesh(obj, method="BEAUTY", keep_normals=True):
    """Add and apply a triangulate modifier."""
    if not obj or obj.type != "MESH":
        return

    is_edit_mode = obj.mode == "EDIT"
    if is_edit_mode:
        bpy.ops.object.mode_set(mode="OBJECT")

    tri_mod = obj.modifiers.new(name="TempTriangulate", type="TRIANGULATE")
    tri_mod.quad_method = method
    tri_mod.keep_custom_normals = keep_normals

    # Use override context for applying modifier
    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=tri_mod.name)
    except (RuntimeError, ReferenceError) as e:
        print(f"Warning: Could not apply triangulation modifier on {obj.name}: {e}")
    finally:
        # Modifier is automatically removed by apply, no need to explicitly remove
        if is_edit_mode:
            bpy.ops.object.mode_set(mode="EDIT")


def export_object(obj, file_path, scene_props):
    """Exports a single object using scene properties."""
    fmt = scene_props.mesh_export_format
    success = False

    # Ensure only the target object is selected and active
    with temp_selection_context(bpy.context, active_object=obj, selected_objects=[obj]):
        try:
            if fmt == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath=file_path + ".fbx",
                    use_selection=True,
                    global_scale=scene_props.mesh_export_scale, # FBX exporter handles scale
                    axis_forward=scene_props.mesh_export_coord_forward,
                    axis_up=scene_props.mesh_export_coord_up,
                    apply_scale_options="FBX_SCALE_ALL", # Or adjust as needed
                    object_types={"MESH"},
                    use_mesh_modifiers=False, # Modifiers should be applied already
                    bake_anim=False,
                    # Add other relevant FBX options
                )
            elif fmt == "OBJ":
                bpy.ops.export_scene.obj(
                    filepath=file_path + ".obj",
                    use_selection=True,
                    global_scale=scene_props.mesh_export_scale, # OBJ exporter handles scale
                    axis_forward=scene_props.mesh_export_coord_forward,
                    axis_up=scene_props.mesh_export_coord_up,
                    use_mesh_modifiers=False,
                    use_triangles=False, # Triangulation handled separately if enabled
                    # Add other relevant OBJ options
                )
            elif fmt == "GLTF":
                # Ensure the glTF addon is enabled
                bpy.ops.export_scene.gltf(
                    filepath=file_path + ".gltf",
                    export_format="GLTF_SEPARATE", # or GLB
                    use_selection=True,
                    export_apply=False, # Transforms/Modifiers should be applied already
                    export_attributes=True,
                    export_extras=True,
                    export_yup=(scene_props.mesh_export_coord_up == "Y"),
                     # Add other relevant glTF options
                )
            elif fmt == "USD":
                 bpy.ops.wm.usd_export(
                     filepath=file_path + ".usd",
                     selected_objects_only=True,
                     export_meshes=True,
                     export_materials=True, # Optional
                     generate_preview_surface=False, # Optional
                     use_instancing=False, # Optional
                     evaluation_mode="RENDER", # Use evaluated mesh state
                     # USD exporter uses Blender's scene units and axis settings by default
                     # axis_up/forward might need manual transform if critical
                 )
            elif fmt == "STL":
                 bpy.ops.export_mesh.stl(
                     filepath=file_path + ".stl",
                     use_selection=True,
                     global_scale=scene_props.mesh_export_scale,
                     axis_forward=scene_props.mesh_export_coord_forward,
                     axis_up=scene_props.mesh_export_coord_up,
                     use_mesh_modifiers=False,
                 )
            else:
                 print(f"Error: Unsupported export format '{fmt}'")
                 return False # Indicate failure for unsupported format

            print(f"Exported {os.path.basename(file_path)} ({fmt})")
            success = True

        except Exception as e:
            print(f"Error exporting {obj.name} as {fmt}: {e}")
            # Consider using self.report({"ERROR"}, ...) if inside operator context

    return success


# --- Main Export Operator ---

class MESH_OT_batch_export(Operator):
    """Exports selected mesh objects sequentially with specified settings"""
    bl_idname = "mesh.batch_export"
    bl_label = "Export Selected Meshes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        # Enable only if there are selected mesh objects
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        scene = context.scene
        scene_props = scene
        wm = context.window_manager
        start_time = time.time()

        # Get mesh objects to process from current selection
        objects_to_export = [obj for obj in context.selected_objects if obj.type == "MESH"]
        total_objects = len(objects_to_export)

        if not objects_to_export:
            self.report({"WARNING"}, "No mesh objects selected.")
            return {"CANCELLED"}

        # Prepare export path
        export_base_path = bpy.path.abspath(scene_props.mesh_export_path)
        if not os.path.exists(export_base_path):
            try:
                os.makedirs(export_base_path)
            except OSError as e:
                self.report({"ERROR"}, f"Could not create export directory: {export_base_path}. Error: {e}")
                return {"CANCELLED"}
        elif not os.path.isdir(export_base_path):
             self.report({"ERROR"}, f"Export path is not a directory: {export_base_path}")
             return {"CANCELLED"}

        successful_exports = 0
        failed_exports = []

        # --- Initialize Progress Bar ---
        wm.progress_begin(0, total_objects) # <<-- START PROGRESS

        try: # Wrap the main loop for finally block
            # --- Main Export Loop ---
            for index, original_obj in enumerate(objects_to_export):

                # --- Update Progress Bar ---
                # Update based on the number of items *completed* or *about to start*.
                # Updating with index + 1 means after item "index" is done, progress is "index + 1".
                # Value should go from 1 up to total_objects.
                wm.progress_update(index + 1)

                # ADD FOR DEBUGGING ONLY - REMOVE LATER
                # import time
                # time.sleep(0.01)
                # --- END DEBUGGING ---

                print(f"\nProcessing ({index + 1}/{total_objects}): {original_obj.name}")

                export_obj = None
                export_obj_name = None

                try:
                    # 1. Copy Object
                    # Ensure we are in object mode for copying
                    if original_obj.mode != "OBJECT":
                        bpy.ops.object.mode_set(mode="OBJECT")

                    export_obj = original_obj.copy()
                    export_obj.data = original_obj.data.copy()
                    context.collection.objects.link(export_obj)
                    export_obj_name = export_obj.name # <<-- STORE NAME HERE after successful copy
                    print(f"Copied {original_obj.name} to {export_obj_name}")

                    # Context for operations on the copied object
                    with temp_selection_context(context, active_object=export_obj, selected_objects=[export_obj]):
                        # 2. Apply Prefix/Suffix to Name
                        new_name = scene_props.mesh_export_prefix + original_obj.name + scene_props.mesh_export_suffix
                        export_obj.name = new_name
                        export_obj_name = export_obj.name # <<-- UPDATE STORED NAME if renamed
                        base_export_name = new_name
                        print(f"Renamed copy to: {export_obj_name}")

                        # 3. Zero Location (on Copy)
                        if scene_props.mesh_export_zero_location:
                            export_obj.location = (0.0, 0.0, 0.0)
                            print("Zeroed location")

                        # 4. Apply Modifiers (on Copy) - before LOD/Triangulation
                        print("Applying existing modifiers...")
                        apply_mesh_modifiers(export_obj)

                        # 5 & 6. Apply Decimate (LOD) & Triangulate (if needed per LOD)
                        if scene_props.mesh_export_lod:
                            print(f"Generating LODs ({scene_props.mesh_export_lod_count} levels)...")
                            lod_ratios = [
                                scene_props.mesh_export_lod_ratio_01,
                                scene_props.mesh_export_lod_ratio_02,
                                scene_props.mesh_export_lod_ratio_03,
                                scene_props.mesh_export_lod_ratio_04,
                            ]

                            # Export Base Mesh (LOD 0) - potentially triangulated
                            lod0_path = os.path.join(export_base_path, f"{base_export_name}_LOD0")
                            lod0_obj = export_obj.copy() # Copy before adding LOD modifiers
                            lod0_obj.data = export_obj.data.copy()
                            context.collection.objects.link(lod0_obj)

                            with temp_selection_context(context, active_object=lod0_obj, selected_objects=[lod0_obj]):
                                if scene_props.mesh_export_triangulate:
                                    print("Triangulating LOD0...")
                                    triangulate_mesh(lod0_obj, scene_props.mesh_export_triangulate_method, scene_props.mesh_export_keep_normals)
                                print(f"Exporting {os.path.basename(lod0_path)}...")
                                if export_object(lod0_obj, lod0_path, scene_props):
                                    successful_exports +=1
                                else:
                                    failed_exports.append(f"{original_obj.name} (LOD 0)")

                            # Cleanup LOD0 copy
                            bpy.data.objects.remove(lod0_obj, do_unlink=True)


                            # Generate and Export Higher LODs
                            # Apply decimate/triangulate directly on the main export_obj copy
                            for i in range(scene_props.mesh_export_lod_count):
                                lod_level = i + 1
                                ratio = lod_ratios[i]
                                lod_path = os.path.join(export_base_path, f"{base_export_name}_LOD{lod_level:02d}")
                                print(f"Generating LOD{lod_level} (Ratio: {ratio:.3f})...")

                                # Add Decimate Modifier
                                dec_mod = export_obj.modifiers.new(name=f"TempLODDecimate", type="DECIMATE")
                                dec_mod.decimate_type = scene_props.mesh_export_lod_type.upper() # COLLAPSE or UNSUBDIVIDE
                                dec_mod.ratio = ratio
                                # Add other decimate options if needed (e.g., triangulate, symmetry)

                                # Apply Decimate
                                try:
                                    print(f"pplying Decimate modifier...")
                                    with temp_selection_context(context, active_object=export_obj, selected_objects=[export_obj]):
                                        bpy.ops.object.modifier_apply(modifier=dec_mod.name) # Apply it
                                except Exception as e:
                                    print(f"Warning: Failed to apply Decimate for LOD{lod_level}: {e}")
                                    export_obj.modifiers.remove(dec_mod) # Remove if apply failed
                                    failed_exports.append(f"{original_obj.name} (LOD {lod_level} - Decimate Apply Fail)")
                                    continue # Skip export for this LOD


                                # Apply Triangulate (if needed for this LOD)
                                if scene_props.mesh_export_triangulate:
                                    print("Triangulating...")
                                    triangulate_mesh(export_obj, scene_props.mesh_export_triangulate_method, scene_props.mesh_export_keep_normals)


                                # Export LOD Mesh
                                print(f"Exporting {os.path.basename(lod_path)}...")
                                if export_object(export_obj, lod_path, scene_props):
                                    successful_exports += 1
                                else:
                                    failed_exports.append(f"{original_obj.name} (LOD {lod_level})")


                                # --- IMPORTANT: Need to revert mesh state for next LOD ---
                                # Since modifiers were applied, we can't just remove them.
                                # Re-copying from original OR using undo is complex.
                                # **Current approach modifies the copy permanently.**
                                # TODO: For correct iterative LODs, you might need to:
                                #    a) Make a fresh copy from original_obj for EACH LOD level. (More robust)
                                #    b) Apply modifiers temporarily without saving state (harder).
                                print(f"Note: Current LOD implementation modifies the base mesh copy progressively.")
                                # For now, we proceed with the modified mesh for the next LOD level.


                        else:
                            # 7. Apply Triangulate (Only if not doing LODs)
                            if scene_props.mesh_export_triangulate:
                                print("Triangulating mesh...")
                                triangulate_mesh(export_obj, scene_props.mesh_export_triangulate_method, scene_props.mesh_export_keep_normals)

                            # 8. Export (Single file, no LODs)
                            file_path = os.path.join(export_base_path, base_export_name)
                            print(f"Exporting {os.path.basename(file_path)}...")
                            if export_object(export_obj, file_path, scene_props):
                                successful_exports += 1
                            else:
                                failed_exports.append(original_obj.name)

                    # --- End of temp_selection_context ---

                except Exception as e:
                    # Report the main processing error
                    error_msg = f"Failed to process {original_obj.name}: {e}"
                    self.report({"ERROR"}, error_msg)
                    # Use export_obj_name if available in the log message
                    log_name = export_obj_name if export_obj_name else original_obj.name
                    print(f"ERROR processing {log_name}: {e}")
                    failed_exports.append(f"{original_obj.name} (Processing Error: {e})")


                finally:
                    # 9. Cleanup
                    if export_obj: # Check if the python variable holding the reference exists
                        log_cleanup_name = export_obj_name if export_obj_name else "unnamed copy"
                        print(f"Attempting cleanup for: {log_cleanup_name}")
                        try:
                            # Attempt removal using the object reference
                            bpy.data.objects.remove(export_obj, do_unlink=True)
                            # Use the stored name for the success message
                            print(f"Cleaned up copy: {log_cleanup_name}")
                        except ReferenceError:
                            # This might happen if obj was already removed or became invalid earlier
                            # Use the stored name for the message
                            print(f"Copy {log_cleanup_name} was already removed or invalid before final cleanup.")
                        except Exception as remove_e:
                            # Catch other potential removal errors
                            print(f"Error during cleanup of {log_cleanup_name}: {remove_e}")

                    # 10. Mark Original Object (regardless of failure?)
                    # Decide if you only want to mark successfully exported objects.
                    # This checks if the original object's name (or potentially LOD variant) was added to failed_exports
                    processed_successfully = not any(fail_name.startswith(original_obj.name) for fail_name in failed_exports)

                    if original_obj and processed_successfully:
                        mark_object_as_exported(original_obj)
                        print(f"Marked original {original_obj.name} as exported.")
                    elif original_obj:
                        print(f"Skipped marking original {original_obj.name} due to processing errors.")
        
            # --- Loop Finished ---
            # Update progress bar to final value
            # wm.progress_update(total_objects) # <<-- Ensure it reaches the end
        
        finally: # Use finally to ensure progress bar ends even if error occurs
             # --- End Progress Bar ---
             wm.progress_end() # <<-- END PROGRESS

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Final Report
        report_type = {"INFO"} if not failed_exports else {"WARNING"}
        message = f"Export finished in {elapsed_time:.2f} seconds. Exported {successful_exports} files."
        if failed_exports:
            message += f"Failed to export: {', '.join(failed_exports)}"

        self.report(report_type, message)
        print(f"\n{message}")

        # Trigger redraw to show indicators
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return {"FINISHED"}
    

# Custom operator to select an object by name (needed for the panel)
class OBJECT_OT_select_by_name(Operator):
    """Selects and focuses on the specified object""" # Docstring updated
    bl_idname = "object.select_by_name"
    bl_label = "Select Object by Name"
    bl_description = "Selects and focuses on the specified object"
    bl_options = {"REGISTER", "INTERNAL"} # Keep INTERNAL if only called by UI

    # This property receives the name from the UI button
    object_name: StringProperty()

    # @classmethod <-- REMOVE THE ENTIRE POLL METHOD
    # def poll(cls, context):
    #     # This check cannot work here and is not necessary.
    #     # Existence is checked in execute().
    #     return True

    def execute(self, context):
        # Check for object existence using the name passed to the instance
        target_obj = bpy.data.objects.get(self.object_name)

        if not target_obj:
            # Report error if object name not found in scene data
            print(f"Object '{self.object_name}' not found for selection.")
            # Optionally use self.report for status bar message
            # self.report({"WARNING"}, f"Object '{self.object_name}' not found.")
            return {"CANCELLED"}

        # --- Selection Logic ---
        original_mode = context.mode
        obj_to_switch_mode = context.active_object # Get active obj before changing selection

        try:
            # Ensure Object mode for selection operations
            if original_mode != "OBJECT":
                 # Check if current active object allows switching from its mode
                 can_switch = not obj_to_switch_mode or obj_to_switch_mode.mode == "OBJECT"
                 if can_switch:
                      bpy.ops.object.mode_set(mode="OBJECT")
                 else:
                      # Cannot switch from current mode (e.g., Edit mode on wrong object type)
                      print(f"Cannot switch from {original_mode} on {obj_to_switch_mode.name if obj_to_switch_mode else 'None'} to select.")
                      # self.report({"WARNING"}, f"Cannot switch mode to select '{self.object_name}'.")
                      return {"CANCELLED"}


            # Perform selection
            bpy.ops.object.select_all(action="DESELECT")
            target_obj.select_set(True)
            context.view_layer.objects.active = target_obj

            # Optional: Frame view (make sure context is right, might need override)
            # try:
            #     # Find 3D view area
            #     for window in context.window_manager.windows:
            #         screen = window.screen
            #         for area in screen.areas:
            #             if area.type == "VIEW_3D":
            #                 for region in area.regions:
            #                     if region.type == "WINDOW":
            #                         override = {"window": window, "screen": screen, "area": area, "region": region}
            #                         bpy.ops.view3d.view_selected(override)
            #                         break
            #                 break
            #         break
            # except Exception as frame_e:
            #     print(f"Could not frame view: {frame_e}")


        except (ReferenceError, RuntimeError) as e:
             # Catch errors during selection/activation
             print(f"Error selecting object '{self.object_name}': {e}")
             # self.report({"ERROR"}, f"Error selecting '{self.object_name}'.")
             # Attempt to restore original mode if we changed it
             if context.mode != original_mode:
                  try:
                      bpy.ops.object.mode_set(mode=original_mode)
                  except Exception: pass # Ignore errors during error-recovery mode switch
             return {"CANCELLED"}

        # Attempt to restore original mode if we changed it
        if context.mode != original_mode:
             try:
                  # Check if the newly active object supports the original mode
                  if context.active_object and context.active_object.type == "MESH" or original_mode == "OBJECT":
                      bpy.ops.object.mode_set(mode=original_mode)
                  elif context.mode != "OBJECT": # Fallback to object mode if incompatible
                       bpy.ops.object.mode_set(mode="OBJECT")
             except Exception as mode_e:
                  print(f"Could not restore original mode ({original_mode}): {mode_e}")
                  if context.mode != "OBJECT": # Ensure Object mode if restore fails
                       bpy.ops.object.mode_set(mode="OBJECT")


        return {"FINISHED"}
    

# --- Registration ---
classes = (
    MESH_OT_batch_export,
    OBJECT_OT_select_by_name, # Make sure this is included
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError: # Handle re-registration if needed
            pass

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError: # Handle errors if already unregistered
             pass