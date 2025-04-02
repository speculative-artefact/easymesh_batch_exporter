import bpy
import os
import bmesh
import time
from bpy.types import Operator
from dataclasses import dataclass
import contextlib
from . import export_indicators
from functools import wraps

COORDINATE_SYSTEMS = {
    "Blender": {"axis_forward": "Y", "axis_up": "Z"},
    "Godot": {"axis_forward": "Z", "axis_up": "Y"},
    "Unity": {"axis_forward": "Z", "axis_up": "Y"},
    "Unreal": {"axis_forward": "X", "axis_up": "Z"},
}

@dataclass
class ExportSettings:
    format_type: str
    axis_forward: str
    axis_up: str
    triangulate: bool
    zero_location: bool
    scale: float
    prefix: str
    suffix: str
    lod_count: int
    lod_ratios: list

# Main export operator
class MESH_OT_batch_export(Operator):
    bl_idname = "mesh.batch_export"
    bl_label = "Export Selected Meshes"
    bl_description = "Export all selected objects as mesh files"
    bl_options = {"REGISTER", "UNDO"}
    
    # Timer for modal operation
    _timer = None
    # Objects to process
    _mesh_objects = []
    # Current object index
    _current_index = 0
    # Starting time for progress reporting
    _start_time = 0
    # Count of successful exports
    _successful_exports = 0
    # Export path
    _export_path = ""
    # Export settings
    _export_settings = None
    
    @classmethod
    def poll(cls, context):
        """Check if the operator can be executed"""
        return len(context.selected_objects) > 0

    def modal(self, context, event):
        """Modal function called during export operation"""
        scene = context.scene
        
        if event.type == 'TIMER':
            # Check if we're done with all objects
            if self._current_index >= len(self._mesh_objects):
                # Reset progress properties
                scene.mesh_export_in_progress = False
                scene.mesh_export_current_object = ""
                
                # Calculate elapsed time and report
                elapsed_time = time.time() - self._start_time
                time_str = self.format_time(elapsed_time)
                
                # Finalize progress bar
                context.window_manager.progress_end()
                
                # Report results
                self.report(
                    {"INFO"}, 
                    f"Successfully exported {self._successful_exports} of {len(self._mesh_objects)} objects to {self._export_path} in {time_str}"
                )
                
                # Remove the timer and finish
                context.window_manager.event_timer_remove(self._timer)
                return {'FINISHED'}
            
            # Get the current object to process
            obj = self._mesh_objects[self._current_index]
            
            # Update progress in scene properties
            scene.mesh_export_progress = self._current_index + 1
            scene.mesh_export_current_object = obj.name
            
            # Update Blender's built-in progress
            progress = (self._current_index + 0.5) / len(self._mesh_objects)
            context.window_manager.progress_update(progress)
            # context.window_manager.progress_update_label(
            #     f"Exporting {self._current_index + 1}/{len(self._mesh_objects)}: {obj.name}"
            # )
            
            # Process this object
            if self.process_single_object(context, obj, self._export_path, self._export_settings):
                self._successful_exports += 1
            
            # Move to the next object
            self._current_index += 1
            
            # Force redraw to update UI
            for area in context.screen.areas:
                area.tag_redraw()
                
            return {'RUNNING_MODAL'}
            
        # Cancel the operation
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Reset progress properties
            scene.mesh_export_in_progress = False
            scene.mesh_export_current_object = ""
            
            context.window_manager.progress_end()
            context.window_manager.event_timer_remove(self._timer)
            self.report({"INFO"}, "Export cancelled")
            return {'CANCELLED'}
            
        return {'PASS_THROUGH'}

    # @ensure_export_cleanup
    def execute(self, context):
        """Initialize and start the export operation"""
        scene = context.scene
        self._start_time = time.time()
        
        self._export_path = self.prepare_export_path(scene)
        
        # Get selected objects efficiently
        self._mesh_objects = [obj for obj in context.selected_objects if obj.type == "MESH"]
        
        if not self._mesh_objects:
            self.report({"WARNING"}, "No mesh objects selected")
            return {"CANCELLED"}
        
        # Get export settings once
        self._export_settings = self.get_export_settings(scene)
        
        # Initialize progress tracking
        self._current_index = 0
        self._successful_exports = 0
        
        # Set scene progress properties
        scene.mesh_export_in_progress = True
        scene.mesh_export_total = len(self._mesh_objects)
        scene.mesh_export_progress = 0
        scene.mesh_export_current_object = "Starting..."
        
        # Start the progress bar
        context.window_manager.progress_begin(0, 1.0)
        # context.window_manager.progress_update_label(f"Starting export of {len(self._mesh_objects)} objects...")
        
        # Add timer for modal execution
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}

    def format_time(self, elapsed_time):
        """Format time nicely for display"""
        if elapsed_time < 1:
            return f"{elapsed_time*1000:.0f} ms"
        elif elapsed_time < 60:
            return f"{elapsed_time:.2f} seconds"
        else:
            minutes = int(elapsed_time // 60)
            seconds = elapsed_time % 60
            return f"{minutes} min {seconds:.1f} sec"
    
    def prepare_export_path(self, scene):
        """
        Prepare the export path based on the scene settings
        
        Args:
            scene: Current Blender scene
        
        Returns:
            str: Export path
        """
        # Get export path from scene properties
        export_path = bpy.path.abspath(scene.mesh_export_path)
        
        # Create export directory if it doesn't exist
        if not os.path.exists(export_path):
            os.makedirs(export_path)
        
        return export_path
    
    def get_export_settings(self, scene):
        """
        Get export settings from the scene
        
        Args:
            scene: Current Blender scene
            
        Returns:
            ExportSettings: An object containing export settings
        """
        # Determine coordinate system for export
        axis_settings = COORDINATE_SYSTEMS.get(scene.mesh_export_axis_simple, COORDINATE_SYSTEMS["Blender"])
        
        return ExportSettings(
            format_type=scene.mesh_export_format,
            axis_forward=axis_settings["axis_forward"],
            axis_up=axis_settings["axis_up"],
            triangulate=scene.mesh_export_triangulate,
            zero_location=scene.mesh_export_zero_location,
            scale=scene.mesh_export_scale,
            prefix=scene.mesh_export_prefix,
            suffix=scene.mesh_export_suffix,
            lod_count=scene.mesh_export_lod,
            lod_ratios=[scene.mesh_export_lod_01, scene.mesh_export_lod_02, scene.mesh_export_lod_03]
        )
    
    def process_single_object(self, context, obj, export_path, export_settings):
        """
        Process a single object for export
        
        Args:
            context: Blender context
            obj: The object to export
            export_path: Path to export directory
            export_settings: Export settings object
            
        Returns:
            bool: True if export was successful, False otherwise
        """
        original_location = None
        
        # Apply zero location if needed
        if export_settings.zero_location:
            original_location = obj.location.copy()
            obj.location = (0, 0, 0)
        
        try:
            # Create the base filename without any LOD suffix
            base_name = export_settings.prefix + obj.name + export_settings.suffix
            base_file_path = os.path.join(export_path, base_name)
            
            # Export base mesh (LOD0)
            main_file_path = f"{base_file_path}_LOD_00" if export_settings.lod_count > 0 else base_file_path
            
            # Export the base mesh
            with temp_selection_context(context, obj, obj):
                self.export_mesh(obj, main_file_path, export_settings.format_type, 
                                context.scene, export_settings.axis_forward, export_settings.axis_up)
            
            # Generate LODs if needed
            if export_settings.lod_count > 0:
                # Create a temporary LOD object
                lod_obj = obj.copy()
                lod_obj.data = obj.data.copy()
                context.collection.objects.link(lod_obj)
                
                try:
                    # Apply zero location to LOD object if needed
                    if export_settings.zero_location:
                        lod_obj.location = (0, 0, 0)
                    
                    # Create each LOD level
                    for lod_level in range(1, min(export_settings.lod_count + 1, 4)):
                        ratio = export_settings.lod_ratios[lod_level - 1]
                        lod_file_path = f"{base_file_path}_LOD_{lod_level:02d}"
                        
                        self.create_and_export_lod(
                            context, lod_obj, lod_file_path, export_settings.format_type,
                            context.scene, lod_level, ratio,
                            export_settings.axis_forward, export_settings.axis_up
                        )
                finally:
                    # Clean up the temporary LOD object
                    bpy.data.objects.remove(lod_obj)
        finally:
            # Restore original location if it was changed
            if export_settings.zero_location and original_location:
                obj.location = original_location
    
    def create_and_export_lod(self, context, obj, lod_file_path, format_type, scene, lod_level, ratio, axis_forward, axis_up):
        """
        Create and export an LOD version of the object
        
        Args:
            context: Blender context
            obj: The object to create LOD from
            lod_file_path: Complete file path for this LOD level (already includes _LODn suffix)
            format_type: Export format (FBX, OBJ, etc.)
            scene: Current scene
            lod_level: LOD level number (1-3)
            ratio: Decimation ratio (0.0-1.0)
            axis_forward: Forward axis for export
            axis_up: Up axis for export
        
        Returns:
            None
        """
        # Add decimate modifier
        decimate = obj.modifiers.new(name=f"LOD{lod_level}_Decimate", type="DECIMATE")
        decimate.ratio = ratio
        
        # Export the LOD mesh (using the path that already has the LOD suffix)
        self.export_mesh(obj, lod_file_path, format_type, scene, axis_forward, axis_up)
        
        # Remove the decimate modifier
        obj.modifiers.remove(decimate)
    

    def export_mesh(self, obj, file_path, format_type, scene, axis_forward, axis_up):
        """
        Export a mesh with the specified format and settings
        
        Args:    
            obj: The mesh object to export
            file_path: Complete file path for the export
            format_type: Export format (FBX, OBJ, etc.)
            scene: Current Blender scene
            axis_forward: Forward axis for export
            axis_up: Up axis for export
        
        Returns:
            bool: True if export was successful, False otherwise
        """
        if not obj or obj.type != "MESH":
            self.report({"ERROR"}, f"Cannot export {obj.name}: Not a mesh object")
            return False
        
        # Common export parameters
        common_params = {
            "filepath": file_path + f".{format_type.lower()}",
            "use_selection": True,
            "axis_forward": axis_forward,
            "axis_up": axis_up,
            "global_scale": scene.mesh_export_scale,
        }
        
        try:
            with temp_selection_context(bpy.context, obj, obj):
                if format_type == "FBX":
                    bpy.ops.export_scene.fbx(
                        **common_params,
                        use_mesh_modifiers=True,
                        use_triangles=False,
                        mesh_smooth_type="FACE",
                        use_custom_props=False,
                        path_mode="COPY",
                        use_metadata=False,
                        apply_scale_options="FBX_SCALE_ALL",
                    )
                elif format_type == "OBJ":
                    # Rename parameters for OBJ export
                    obj_params = {
                        **common_params,
                        "export_selected_objects": True,
                        "forward_axis": axis_forward,
                        "up_axis": axis_up,
                        "apply_modifiers": True,
                        "export_triangulated_mesh": False,
                    }
                    # Remove incompatible params
                    obj_params.pop("use_selection", None)
                    obj_params.pop("axis_forward", None)
                    obj_params.pop("axis_up", None)
                    
                    bpy.ops.wm.obj_export(**obj_params)
                elif format_type == "GLTF":
                    bpy.ops.export_scene.gltf(
                        **common_params,
                        export_format="GLTF_SEPARATE",
                        export_apply=True,
                        export_selected=True,
                        export_materials="EXPORT",
                        export_cameras=False,
                        export_lights=False,
                        export_animations=False,
                    )
                elif format_type == "USD":
                    bpy.ops.wm.usd_export(
                        filepath=common_params["filepath"],
                        selected=True,
                        export_materials="EXPORT",
                        export_animations=False,
                        export_lights=False,
                        export_cameras=False,
                    )
                elif format_type == "STL":
                    bpy.ops.export_mesh.stl(
                        filepath=common_params["filepath"],
                        use_selection=True,
                        global_scale=scene.mesh_export_scale,
                        use_mesh_modifiers=True,
                        ascii=False,
                    )
            
            # Mark the object as exported
            export_indicators.mark_object_as_exported(obj)
            return True
        except Exception as e:
            self.report({"ERROR"}, f"Failed to export {obj.name}: {str(e)}")
            return False

    def apply_mesh_modifiers(self, obj):
        """
        Apply all modifiers to the mesh object
        
        Args:
            obj: The mesh object to apply modifiers to
        
        Returns:
            None
        """
        # Ensure the object is active for modifier operations
        bpy.context.view_layer.objects.active = obj
        
        # Get a list of modifier names first (since modifiers list changes during iteration)
        modifier_names = [modifier.name for modifier in obj.modifiers]
        
        # Apply each modifier by name
        for name in modifier_names:
            try:
                # Check if the modifier still exists (previous operations might have removed it)
                if name in obj.modifiers:
                    bpy.ops.object.modifier_apply(modifier=name)
            except RuntimeError as e:
                self.report({"WARNING"}, f"Error applying modifier {name} to {obj.name}: {str(e)}")

    def triangulate_mesh(self, obj, method="BEAUTY"):
        """
        Apply triangulation to a mesh object using a modifier
        
        Args:
            obj: The mesh object to triangulate
            method: Triangulation method (BEAUTY, FIXED, FIXED_ALTERNATE, SHORTEST_DIAGONAL)
            
        Returns:
            bool: True if triangulation was successful
        """
        if not obj or obj.type != "MESH":
            return False
            
        try:
            # Apply other modifiers first
            self.apply_mesh_modifiers(obj)

            # Add triangulate modifier
            triangulate_mod = obj.modifiers.new(name="Triangulate", type="TRIANGULATE")
            
            # Set triangulation options
            triangulate_mod.quad_method = method
            triangulate_mod.ngon_method = method
            
            # Apply the modifier
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=triangulate_mod.name)
            
            return True
                
        except Exception as e:
            self.report({"ERROR"}, f"Triangulation failed: {str(e)}")
            return False


@contextlib.contextmanager
def temp_selection_context(context, objects_to_select=None, active_object=None):
    """
    Context manager for temporarily changing selection state
    
    Args:
        context: Blender context
        objects_to_select: List of objects to select (or a single object)
        active_object: Object to set as active
    
    Returns:
        None
    """
    # Store original selection and active object
    original_selected = context.selected_objects.copy()
    original_active = context.view_layer.objects.active
    
    try:
        # Deselect all
        bpy.ops.object.select_all(action="DESELECT")
        
        # Select requested objects
        if objects_to_select:
            if not isinstance(objects_to_select, list):
                objects_to_select = [objects_to_select]
            for obj in objects_to_select:
                obj.select_set(True)
        
        # Set active object
        if active_object:
            context.view_layer.objects.active = active_object
        
        yield
    finally:
        # Restore original selection state
        bpy.ops.object.select_all(action="DESELECT")
        for obj in original_selected:
            if obj:  # Check if object still exists
                obj.select_set(True)
        if original_active:
            context.view_layer.objects.active = original_active

class MESH_OT_select_all_meshes(Operator):
    bl_idname = "mesh.select_all_meshes"
    bl_label = "Select All Meshes"
    bl_description = "Select all mesh objects in the scene"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        """Check if there are mesh objects in the scene"""
        return any(obj.type == "MESH" for obj in context.scene.objects)

    def execute(self, context):
        """
        Select all mesh objects in the scene
        
        Args:
            context: Blender context
        
        Returns:
            {"FINISHED"}: Operation completed successfully
        """
        # Deselect all objects first
        bpy.ops.object.select_all(action="DESELECT")
        
        # Count how many mesh objects we'll select
        mesh_count = 0
        
        # Select all mesh objects
        for obj in context.scene.objects:
            if obj.type == "MESH":
                obj.select_set(True)
                mesh_count += 1
                
                # Make the last selected mesh the active object
                context.view_layer.objects.active = obj
        
        # Report how many objects were selected
        self.report({"INFO"}, f"Selected {mesh_count} mesh objects")
        return {"FINISHED"}

classes = (
    MESH_OT_batch_export,
    MESH_OT_select_all_meshes,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

def ensure_export_cleanup(func):
    """Decorator to ensure export properties are reset even if an exception occurs"""
    @wraps(func)
    def wrapper(self, context, *args, **kwargs):
        try:
            return func(self, context, *args, **kwargs)
        except Exception as e:
            # Reset scene properties
            context.scene.mesh_export_in_progress = False
            context.scene.mesh_export_current_object = ""
            
            # Clean up progress
            try:
                context.window_manager.progress_end()
            except:
                pass
                
            # Clean up timer
            if hasattr(self, "_timer") and self._timer:
                try:
                    context.window_manager.event_timer_remove(self._timer)
                except:
                    pass
                    
            # Re-raise the exception
            raise e
    return wrapper