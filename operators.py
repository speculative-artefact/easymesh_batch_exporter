# operators.py
"""
Contains Blender operators for the Mesh Exporter add-on.
Handles batch export of selected mesh objects, including LOD generation,
texture compression, and cleanup of temporary objects.
"""

import bpy
import os
import time
import contextlib
import re
import math
import logging
from bpy.types import Operator
from bpy.props import StringProperty
from . import export_indicators

# --- Setup Logger ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(name)s:%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # Default level

# --- Constants ---
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"

# Large mesh thresholds
LARGE_MESH_THRESHOLD = 500000  # 500K polygons
VERY_LARGE_MESH_THRESHOLD = 1000000  # 1M polygons


# --- Custom Exceptions ---

class MeshExportError(Exception):
    """Base exception for mesh export operations."""
    pass


class ValidationError(MeshExportError):
    """Raised when input validation fails."""
    pass


class ResourceError(MeshExportError):
    """Raised when resource operations fail (files, memory, etc.)."""
    pass


class ProcessingError(MeshExportError):
    """Raised when mesh processing operations fail."""
    pass


class ExportFormatError(MeshExportError):
    """Raised when export format operations fail."""
    pass


# --- Context Managers for Safe Resource Management ---

@contextlib.contextmanager
def temporary_mesh(mesh_data, name="temp_mesh"):
    """Context manager for temporary mesh data that ensures cleanup.
    
    Args:
        mesh_data: The mesh data to manage
        name: Name identifier for logging
        
    Yields:
        The mesh data object
    """
    try:
        yield mesh_data
    finally:
        if mesh_data:
            try:
                bpy.data.meshes.remove(mesh_data)
                logger.debug(f"Cleaned up temporary mesh: {name}")
            except (ReferenceError, Exception) as e:
                logger.warning(f"Failed to cleanup temporary mesh {name}: {e}")


@contextlib.contextmanager
def temporary_object(obj, name=None):
    """Context manager for temporary objects that ensures cleanup.
    
    Args:
        obj: The Blender object to manage
        name: Name identifier for logging (uses obj.name if not provided)
        
    Yields:
        The object
    """
    obj_name = name or (obj.name if obj else "unknown")
    try:
        yield obj
    finally:
        cleanup_object(obj, obj_name)


@contextlib.contextmanager
def temporary_image_file(filepath):
    """Context manager for temporary image files that ensures cleanup.
    
    Args:
        filepath: Path to the temporary file
        
    Yields:
        The filepath
    """
    try:
        yield filepath
    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.debug(f"Cleaned up temporary file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file {filepath}: {e}")


# --- Memory Management Utilities ---

class MemoryManager:
    """Centralised memory management to avoid excessive gc.collect() calls."""
    
    _last_gc_time = 0
    _gc_interval = 5.0  # Minimum seconds between gc.collect() calls
    _pending_cleanup = False
    
    @classmethod
    def request_cleanup(cls, force=False):
        """Request garbage collection, but throttle to avoid performance issues."""
        current_time = time.time()
        
        if force or (current_time - cls._last_gc_time) >= cls._gc_interval:
            import gc
            gc.collect()
            cls._last_gc_time = current_time
            cls._pending_cleanup = False
            logger.debug(f"Garbage collection performed (forced={force})")
        else:
            cls._pending_cleanup = True
            logger.debug("Garbage collection deferred (too frequent)")
    
    @classmethod
    def cleanup_if_pending(cls):
        """Perform cleanup if it was previously deferred."""
        if cls._pending_cleanup:
            cls.request_cleanup(force=True)


class MeshOperations:
    """Common mesh operations to reduce code duplication."""
    
    @staticmethod
    def update_mesh_data(obj, with_memory_cleanup=False):
        """Update mesh data and optionally trigger memory cleanup for large meshes."""
        if not obj or not obj.data:
            return
            
        obj.data.update()
        
        if with_memory_cleanup:
            poly_count = len(obj.data.polygons) if hasattr(obj.data, 'polygons') else 0
            if poly_count > LARGE_MESH_THRESHOLD:
                MemoryManager.request_cleanup()
                logger.debug(f"Memory cleanup after mesh update for {obj.name} ({poly_count:,} polygons)")
    
    @staticmethod
    def update_view_layer():
        """Update view layer with error handling."""
        try:
            bpy.context.view_layer.update()
        except Exception as e:
            logger.warning(f"Failed to update view layer: {e}")
    
    @staticmethod
    def safe_mode_set(obj, mode):
        """Safely set object mode with error handling."""
        if not obj:
            return False
            
        try:
            current_mode = obj.mode
            if current_mode != mode:
                bpy.ops.object.mode_set(mode=mode)
                return True
        except Exception as e:
            logger.warning(f"Failed to set mode {mode} on {obj.name}: {e}")
            return False
        return False


# --- Memory Optimisation Functions ---

def optimise_for_large_mesh(obj):
    """
    Memory optimisation for large meshes.
    
    Args:
        obj (bpy.types.Object): The mesh object to optimise.
        
    Returns:
        bool: True if optimisation was applied, False otherwise.
    """
    if not obj or obj.type != "MESH" or not obj.data:
        return False
        
    poly_count = len(obj.data.polygons)
    if poly_count > LARGE_MESH_THRESHOLD:
        logger.info(f"Applying memory optimisation for large mesh: {poly_count} polygons")
        MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)
        return True
    return False


@contextlib.contextmanager
def safe_large_mesh_operation(obj, operation_name):
    """
    Context manager for operations on large meshes with memory management.
    
    Args:
        obj (bpy.types.Object): The mesh object.
        operation_name (str): Name of the operation for logging.
    """
    poly_count = len(obj.data.polygons) if obj and obj.data else 0
    is_large = poly_count > LARGE_MESH_THRESHOLD
    
    if is_large:
        logger.info(f"Starting large mesh operation: {operation_name} on {poly_count:,} polygons")
        # Pre-operation cleanup
        MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)
        
    try:
        yield
    finally:
        if is_large:
            # Post-operation cleanup
            MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)
            logger.info(f"Completed large mesh operation: {operation_name}")


# --- Core Functions ---


@contextlib.contextmanager
def temp_selection_context(context, active_object=None, selected_objects=None):
    """
    Temporarily set the active object and selection using direct API.
    
    Args:
        context (bpy.context): The current Blender context.
        active_object (bpy.types.Object, optional): 
            The object to set as active.
        selected_objects (list, optional): List of objects to select.
    
    Returns:
        None
    """
    # Store original state
    original_active = context.view_layer.objects.active
    original_selected = [obj for obj in context.scene.objects 
                         if obj.select_get()]
    
    try:
        # Deselect all objects directly
        for obj in context.scene.objects:
            if obj.select_get():
                obj.select_set(False)
        
        # Select requested objects directly
        if selected_objects:
            if not isinstance(selected_objects, list):
                selected_objects = [selected_objects]
            
            for obj in selected_objects:
                if obj and obj.name in context.scene.objects:
                    try:
                        obj.select_set(True)
                    except ReferenceError:
                        logger.warning(f"Could not select '{obj.name}' "
                                       f"- object reference invalid.")
        
        # Set active object directly
        if active_object and active_object.name in context.scene.objects:
            context.view_layer.objects.active = active_object
        elif selected_objects:
            for obj in selected_objects:
                if obj and obj.name in context.scene.objects:
                    context.view_layer.objects.active = obj
                    break
        
        yield
    
    finally:
        # Restore original state directly
        for obj in context.scene.objects:
            obj.select_set(False)
            
        for obj in original_selected:
            if obj and obj.name in context.scene.objects:
                try:
                    obj.select_set(True)
                except ReferenceError:
                    pass
        
        if original_active and original_active.name in context.scene.objects:
            try:
                context.view_layer.objects.active = original_active
            except ReferenceError:
                pass


def convert_curve_to_mesh_object(curve_obj, context):
    """
    Creates a new mesh object from a curve/metaball object and returns it.
    The original curve/metaball object is deleted.
    
    Args:
        curve_obj (bpy.types.Object): The curve/metaball object to convert.
        context (bpy.context): The current Blender context.
        
    Returns:
        bpy.types.Object: The new mesh object.
    """
    if not curve_obj or curve_obj.type not in ["CURVE", "META"]:
        return curve_obj
        
    logger.info(f"Converting {curve_obj.type} object '{curve_obj.name}' to mesh...")
    
    try:
        # Store the original name and properties
        original_name = curve_obj.name
        original_location = curve_obj.location.copy()
        original_rotation = curve_obj.rotation_euler.copy()
        original_scale = curve_obj.scale.copy()
        
        # Get the dependency graph
        depsgraph = context.evaluated_depsgraph_get()
        
        # For metaballs, we need to ensure the view layer is updated
        if curve_obj.type == "META":
            # Debug metaball properties
            metaball = curve_obj.data
            logger.info(f"Metaball threshold: {metaball.threshold}")
            logger.info(f"Metaball elements count: {len(metaball.elements)}")
            if len(metaball.elements) > 0:
                for i, element in enumerate(metaball.elements):
                    logger.info(f"Element {i}: type={element.type}, size_x={element.size_x}, co={element.co}")
            
            # Force view layer update to ensure metaball is evaluated
            context.view_layer.update()
            # Update depsgraph
            depsgraph.update()
        
        # Get the evaluated object
        obj_eval = curve_obj.evaluated_get(depsgraph)
        
        # Create mesh from the evaluated object
        # For metaballs, we must use to_mesh() method
        if curve_obj.type == "META":
            # For metaballs, try getting mesh from the original object first
            # as duplicated metaballs might not evaluate properly
            original_eval = curve_obj.evaluated_get(depsgraph)
            mesh = original_eval.to_mesh()
            logger.info(f"Metaball mesh vertices from original: {len(mesh.vertices) if mesh else 0}")
            
            # If still empty, the metaball might have evaluation issues
            if mesh and len(mesh.vertices) == 0:
                # Try forcing a scene update and re-evaluation
                bpy.context.view_layer.update()
                depsgraph = context.evaluated_depsgraph_get()
                original_eval = curve_obj.evaluated_get(depsgraph)
                original_eval.to_mesh_clear()  # Clear previous attempt
                mesh = original_eval.to_mesh()
                logger.info(f"Metaball mesh vertices after scene update: {len(mesh.vertices) if mesh else 0}")
        else:
            mesh = bpy.data.meshes.new_from_object(obj_eval)
        
        # Verify mesh has geometry
        if mesh and len(mesh.vertices) == 0:
            logger.warning(f"Mesh created from {curve_obj.type} is empty!")
            # For metaballs, this might mean no elements or too high threshold
            if curve_obj.type == "META":
                logger.warning("Check metaball threshold and element positions")
        
        if mesh:
            # For metaballs, we need to copy the evaluated mesh to main database
            if curve_obj.type == "META":
                # Create a new mesh in main database and copy data
                main_mesh = bpy.data.meshes.new(name=original_name)
                main_mesh.from_pydata([v.co for v in mesh.vertices], mesh.edges, [p.vertices for p in mesh.polygons])
                main_mesh.update()
                # Clean up the evaluated mesh
                obj_eval.to_mesh_clear()
                mesh = main_mesh
            
            # Create a new mesh object
            mesh_obj = bpy.data.objects.new(name=original_name, object_data=mesh)
            
            # Copy transforms
            mesh_obj.location = original_location
            mesh_obj.rotation_euler = original_rotation
            mesh_obj.scale = original_scale
            
            # Copy other important properties
            mesh_obj.parent = curve_obj.parent
            mesh_obj.matrix_world = curve_obj.matrix_world.copy()
            
            # Link to the same collections
            for collection in curve_obj.users_collection:
                collection.objects.link(mesh_obj)
            
            # Remove the curve object
            bpy.data.objects.remove(curve_obj, do_unlink=True)
            
            logger.info(f"Successfully converted to mesh object '{mesh_obj.name}'")
            return mesh_obj
        else:
            raise RuntimeError(f"Failed to create mesh from {curve_obj.type}")
            
    except Exception as e:
        logger.error(f"Failed to convert '{curve_obj.name}' to mesh: {e}")
        raise RuntimeError(f"Failed to convert {curve_obj.type} to mesh: {e}") from e


def create_lod_hierarchy(base_obj, lod_objects, collection_name, context):
    """
    Creates a parent/child hierarchy for LODs suitable for game engines.
    
    Args:
        base_obj (bpy.types.Object): The base LOD0 object.
        lod_objects (list): List of LOD objects (LOD1, LOD2, etc.).
        collection_name (str): Name of the original collection.
        context (bpy.context): The current Blender context.
        
    Returns:
        bpy.types.Object: The parent empty object with LODs as children.
    """
    # Create an empty parent object
    parent_empty = bpy.data.objects.new(name=f"{collection_name}_LODGroup", object_data=None)
    parent_empty.empty_display_type = 'PLAIN_AXES'
    parent_empty.empty_display_size = 1.0
    
    # Link to scene
    context.collection.objects.link(parent_empty)
    
    # Set parent for base object and LODs
    base_obj.parent = parent_empty
    base_obj.name = f"{collection_name}_LOD0"
    
    for i, lod_obj in enumerate(lod_objects, start=1):
        lod_obj.parent = parent_empty
        lod_obj.name = f"{collection_name}_LOD{i}"
    
    logger.info(f"Created LOD hierarchy with {len(lod_objects) + 1} levels")
    return parent_empty


def merge_collection_objects(collection, context):
    """
    Merges all mesh objects in a collection into a single mesh.
    
    Args:
        collection (bpy.types.Collection): The collection to merge.
        context (bpy.context): The current Blender context.
        
    Returns:
        bpy.types.Object: The merged mesh object.
        
    Raises:
        ValidationError: If collection is empty or has no meshes
        ProcessingError: If merging fails
    """
    import bmesh
    
    # Get all mesh objects in the collection (including converted curves/metaballs)
    mesh_objects = []
    temp_objects = []  # Track temporary objects for cleanup
    
    for obj in collection.objects:
        if obj.type == 'MESH':
            # Check if object has geometry nodes with instances
            has_instance_geo_nodes = False
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.show_viewport:
                    # This could potentially output instances
                    has_instance_geo_nodes = True
                    logger.info(f"Object '{obj.name}' has geometry nodes modifier")
            mesh_objects.append(obj)
        elif obj.type == 'CURVE':
            # Convert curve to mesh first
            try:
                converted = convert_curve_to_mesh_object(obj.copy(), context)
                mesh_objects.append(converted)
                temp_objects.append(converted)
            except Exception as e:
                logger.warning(f"Failed to convert curve {obj.name} to mesh: {e}")
                continue
        elif obj.type == 'META':
            # Convert metaball to mesh first
            try:
                copy_obj, temp_meta = create_export_copy(obj, context)
                mesh_objects.append(copy_obj)
                if temp_meta:
                    temp_objects.append(temp_meta)
                temp_objects.append(copy_obj)
            except Exception as e:
                logger.warning(f"Failed to convert metaball {obj.name} to mesh: {e}")
                continue
        elif obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION':
            # Handle collection instances (often from geometry nodes)
            logger.info(f"Skipping collection instance '{obj.name}' - would need recursive processing")
    
    if not mesh_objects:
        raise ValidationError(f"Collection '{collection.name}' contains no valid mesh objects")
    
    try:
        # Create a new bmesh object
        bm = bmesh.new()
        
        # Track material remapping
        material_map = {}
        merged_materials = []
        
        for obj in mesh_objects:
            # Get the evaluated mesh with modifiers applied (including geometry nodes)
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)
            
            # Use preserve_all_data_layers to keep custom attributes from geo nodes
            mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            
            # Check if this object has geometry nodes and log it
            has_geo_nodes = any(m.type == 'NODES' for m in obj.modifiers if m.show_viewport)
            if has_geo_nodes:
                logger.info(f"Object '{obj.name}' has geometry nodes - applying to mesh")
            
            # Create a transformation matrix
            transform_matrix = obj.matrix_world
            
            # Add materials and create mapping
            material_offset = len(merged_materials)
            for mat in obj.data.materials:
                if mat:
                    merged_materials.append(mat)
            
            # Create temporary bmesh for this object
            temp_bm = bmesh.new()
            temp_bm.from_mesh(mesh)
            
            # Apply transformation
            temp_bm.transform(transform_matrix)
            
            # Remap material indices
            for face in temp_bm.faces:
                face.material_index += material_offset
            
            # Merge into main bmesh
            temp_mesh = bpy.data.meshes.new(name="temp")
            temp_bm.to_mesh(temp_mesh)
            bm.from_mesh(temp_mesh)
            bpy.data.meshes.remove(temp_mesh)
            temp_bm.free()
            
            # Clean up evaluated mesh
            obj_eval.to_mesh_clear()
        
        # Remove duplicate vertices
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        
        # Create the final mesh
        merged_mesh = bpy.data.meshes.new(name=f"{collection.name}_merged")
        bm.to_mesh(merged_mesh)
        bm.free()
        
        # Create the merged object
        merged_obj = bpy.data.objects.new(name=f"{collection.name}_LOD0", object_data=merged_mesh)
        
        # Assign materials
        for mat in merged_materials:
            merged_obj.data.materials.append(mat)
        
        # Link to scene
        context.collection.objects.link(merged_obj)
        
        # Clean up temporary objects
        for temp_obj in temp_objects:
            bpy.data.objects.remove(temp_obj, do_unlink=True)
        
        logger.info(f"Successfully merged {len(mesh_objects)} objects from collection '{collection.name}'")
        return merged_obj
        
    except Exception as e:
        # Clean up on failure
        for temp_obj in temp_objects:
            try:
                bpy.data.objects.remove(temp_obj, do_unlink=True)
            except:
                pass
        raise ProcessingError(f"Failed to merge collection: {e}") from e


def create_export_copy(original_obj, context):
    """
    Creates a linked copy of the object and its data without mode switching.
    
    Args:
        original_obj (bpy.types.Object): The original object to copy.
        context (bpy.context): The current Blender context.
        
    Returns:
        tuple: (copied_object, temp_metaball_mesh_to_cleanup or None)
        
    Raises:
        ValidationError: If object type is invalid
        ProcessingError: If copying fails
    """
    if not original_obj:
        raise ValidationError("Cannot copy None object")
    
    if original_obj.type not in ["MESH", "CURVE", "META"]:
        raise ValidationError(f"Invalid object type '{original_obj.type}' for copying")
    
    temp_metaball_mesh = None
    
    # For metaballs, convert to mesh first, then duplicate the mesh
    if original_obj.type == "META":
        logger.info(f"Converting metaball '{original_obj.name}' to mesh before duplication...")
        try:
            # Convert the original metaball to mesh in-place
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = original_obj.evaluated_get(depsgraph)
            mesh = obj_eval.to_mesh()
            
            if mesh and len(mesh.vertices) > 0:
                # Create a new mesh object with the converted mesh
                new_mesh = bpy.data.meshes.new(name=f"{original_obj.name}_mesh")
                new_mesh.from_pydata([v.co for v in mesh.vertices], [e.vertices for e in mesh.edges], [p.vertices for p in mesh.polygons])
                new_mesh.update()
                
                mesh_obj = bpy.data.objects.new(name=f"{original_obj.name}_converted", object_data=new_mesh)
                mesh_obj.location = original_obj.location
                mesh_obj.rotation_euler = original_obj.rotation_euler  
                mesh_obj.scale = original_obj.scale
                mesh_obj.matrix_world = original_obj.matrix_world.copy()
                
                # Transfer materials from original metaball to mesh
                if original_obj.data.materials:
                    for mat in original_obj.data.materials:
                        if mat:
                            mesh_obj.data.materials.append(mat)
                    logger.info(f"Transferred {len(original_obj.data.materials)} materials to converted mesh")
                
                # Link to scene temporarily for duplication
                context.collection.objects.link(mesh_obj)
                
                # Clean up the evaluated mesh
                obj_eval.to_mesh_clear()
                
                logger.info(f"Successfully converted metaball to mesh: {mesh_obj.name}")
                # Store the temporary mesh object for cleanup later
                temp_metaball_mesh = mesh_obj
                # Now continue with normal duplication of the mesh object
                original_obj = mesh_obj
            else:
                logger.error("Metaball produced empty mesh")
                raise RuntimeError("Metaball conversion resulted in empty mesh")
                
        except Exception as e:
            logger.error(f"Failed to convert metaball to mesh: {e}")
            raise ProcessingError(f"Metaball to mesh conversion failed: {e}") from e
        
    logger.info(f"Attempting to duplicate '{original_obj.name}' "
                f"using operator...")
    
    # Use the context manager to handle selection and active object
    with temp_selection_context(context, 
                                active_object=original_obj, 
                                selected_objects=[original_obj]):
        try:
            # Duplicate the active object (linked)
            # more direct and conventional way to perform a non-interactive 
            # linked duplication than bpy.ops.object.duplicate(linked=True)
            bpy.ops.object.duplicate_move_linked(
                OBJECT_OT_duplicate={"linked":True, "mode":'TRANSLATION'}, 
                TRANSFORM_OT_translate={"value":(0, 0, 0)} # No actual move
            )
            
            # The new duplicate becomes the active object 
            # after the operator runs
            copy_obj = context.view_layer.objects.active
            logger.info(f"Successfully created duplicate "
                        f"'{copy_obj.name}' via operator.")
            
            # Make data single user FIRST for curves/metaballs to ensure we don't affect the original
            if copy_obj and copy_obj.type in ["CURVE", "META"]:
                if copy_obj.data and copy_obj.data.users > 1:
                    logger.info(f"Making {copy_obj.type.lower()} data single user for '{copy_obj.name}'")
                    copy_obj.data = copy_obj.data.copy()
                # Now convert to mesh - this returns a new object
                copy_obj = convert_curve_to_mesh_object(copy_obj, context)
            
            # Make Mesh Data Single User (for regular meshes or after conversion)
            if copy_obj and copy_obj.data and copy_obj.data.users > 1:
                logger.info(f"Making mesh data single user for "
                            f"'{copy_obj.name}'")
                copy_obj.data = copy_obj.data.copy()
                
                # Optimise memory for large meshes after making single user
                optimise_for_large_mesh(copy_obj)

            return copy_obj, temp_metaball_mesh
            
        except Exception as e:
            logger.error(f"Error using duplicate_move_linked operator for "
                         f"'{original_obj.name}': {e}", exc_info=True)
            # Attempt cleanup if copy_obj was created but failed later
            copy_obj_ref = None
            try:
                copy_obj_ref = context.view_layer.objects.active 
                if copy_obj_ref and copy_obj_ref != original_obj:
                    logger.info(f"Attempting cleanup of partially created "
                                f"copy: {copy_obj_ref.name}")
                    bpy.data.objects.remove(copy_obj_ref, do_unlink=True)
            except Exception as cleanup_e:
                 logger.warning(f"Issue during cleanup after copy "
                                f"failure: {cleanup_e}")

            raise RuntimeError(
                f"Failed to create operator copy of {original_obj.name}: {e}"
            ) from e


def sanitise_filename(name):
    """
    Remove characters that are problematic in filenames.
    
    Args:
        name (str): The name to sanitise.
    
    Returns:
        str: The sanitised name.
    """
    # Replace invalid characters with underscores
    sanitised = re.sub(r'[\\/:*?"<>|.]', '_', name)
    return sanitised


def apply_naming_convention(name, convention):
    """
    Apply specific naming convention to a filename.
    
    Args:
        name (str): The name to convert
        convention (str): The convention to apply ("DEFAULT", "UNREAL", "UNITY")
    
    Returns:
        str: The converted name
    """
    if convention == "DEFAULT":
        # For default, just sanitise normally
        return sanitise_filename(name)
    
    elif convention == "UNREAL":
        # Unreal Engine: PascalCase, no spaces, remove illegal chars
        try:
            # Replace all illegal/separator characters with spaces for splitting
            # This includes: \ / : * ? " < > | . - 
            temp_name = re.sub(r'[\\/:*?"<>|.\-]', ' ', name)
            
            # Handle underscores: check if this looks like a known Unreal prefix
            # Common Unreal prefixes: SM_ (Static Mesh), SK_ (Skeletal Mesh), BP_ (Blueprint), etc.
            known_prefixes = {'SM', 'SK', 'BP', 'M', 'T', 'MT', 'MI', 'A', 'S', 'E', 'W', 'P'}
            prefix = ""
            if '_' in temp_name and len(temp_name) > 4:  # Make sure string is long enough
                parts = temp_name.split('_', 1)
                if len(parts) > 0 and parts[0].upper() in known_prefixes:  # Known Unreal prefix
                    prefix = parts[0].upper() + '_'
                    temp_name = parts[1] if len(parts) > 1 else ""
            
            # Split on spaces and underscores for PascalCase conversion
            temp_name = temp_name.replace('_', ' ')
            words = [w for w in temp_name.split() if w]
            
            # Capitalise each word for PascalCase
            pascal_case = ''.join(word.capitalise() for word in words)
            
            # Make sure we return a valid name
            result = prefix + pascal_case
            if not result:  # Fallback if something went wrong
                result = "Unnamed"
            
            return result
            
        except Exception as e:
            # Fallback to standard sanitisation on any error
            return sanitise_filename(name)
    
    elif convention == "UNITY":
        # Unity: More flexible, capitalise words, keep underscores
        try:
            # First sanitise illegal chars and replace spaces with underscores
            temp_name = re.sub(r'[\\/:*?"<>|.]', '_', name)
            temp_name = temp_name.replace(' ', '_')
            # Replace multiple underscores with single
            temp_name = re.sub(r'_+', '_', temp_name)
            # Remove leading/trailing underscores
            temp_name = temp_name.strip('_')
            # Split, capitalise, rejoin
            parts = temp_name.split('_')
            parts = [p.capitalize() if p else '' for p in parts]
            result = '_'.join(filter(None, parts))  # Filter out empty strings
            return result if result else sanitise_filename(name)
        except Exception:
            return sanitise_filename(name)
    
    elif convention == "GODOT":
        # Godot: snake_case naming (all lowercase with underscores)
        try:
            # First sanitise illegal chars and replace with spaces for processing
            temp_name = re.sub(r'[\\/:*?"<>|.\-]', ' ', name)
            temp_name = temp_name.replace('_', ' ')  # Convert existing underscores to spaces
            
            # Split into words (handles both spaces and case changes)
            # This regex splits on spaces, and also splits on case changes (camelCase -> camel Case)
            words = re.findall(r'[A-Z]*[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]|[0-9]+', temp_name)
            
            # Convert all words to lowercase and join with underscores
            words = [word.lower() for word in words if word and word.strip()]
            result = '_'.join(words)
            
            # Clean up multiple underscores and remove leading/trailing ones
            result = re.sub(r'_+', '_', result).strip('_')
            
            return result if result else sanitise_filename(name).lower().replace(' ', '_')
            
        except Exception:
            # Fallback: basic conversion to snake_case
            temp_name = sanitise_filename(name).lower().replace(' ', '_')
            return re.sub(r'_+', '_', temp_name).strip('_')
    
    return sanitise_filename(name)  # Fallback to standard sanitisation


def setup_export_object(obj, original_obj_name, scene_props, lod_level=None):
    """
    Renames object, applies prefix/suffix/LOD naming, zeros location.
    
    Args:
        obj (bpy.types.Object): The object to set up for export.
        original_obj_name (str): The original name of the object.
        scene_props (bpy.types.PropertyGroup): Scene properties for export.
        lod_level (int, optional): LOD level for naming. Defaults to None.
    
    Returns:
        tuple: The final name, base name, and export scale of the object.
    """
    if not obj:
        return None, None
    try:
        # Remove any existing LOD suffix if re-processing the same object
        if "_LOD" in original_obj_name:
            original_obj_name = original_obj_name.split("_LOD")[0]
        
        # Apply naming convention (this handles sanitisation internally)
        original_obj_name = apply_naming_convention(original_obj_name, scene_props.mesh_export_naming_convention)
        
        # Apply prefix and suffix
        base_name = (
            scene_props.mesh_export_prefix +
            original_obj_name +
            scene_props.mesh_export_suffix
        )
        
        # Truncate if name too long (conservatively 100 chars)
        max_base_length = 100
        if len(base_name) > max_base_length:
            truncated = base_name[:max_base_length-3] + "..."
            logger.warning(
                f"Name too long, truncating: {base_name} → {truncated}"
            )
            base_name = truncated
            
        final_name = (
            f"{base_name}_LOD{lod_level:02d}"
            if lod_level is not None
            else base_name
        )
        obj.name = final_name
        logger.info(f"Renamed to: {obj.name}")

        # Check if object's scale is already 1.0
        scale_epsilon = 1e-6
        if (abs(obj.scale[0] - 1.0) > scale_epsilon or 
            abs(obj.scale[1] - 1.0) > scale_epsilon or 
            abs(obj.scale[2] - 1.0) > scale_epsilon):
            # Apply scale transform if not 1.0
            logger.info(f"Object scale is not 1.0: {obj.scale}, applying...")
            apply_transforms(obj, apply_scale=True)

        # Zero location if specified in scene properties
        if scene_props.mesh_export_zero_location:
            obj.location = (0.0, 0.0, 0.0)
            logger.info(f"Zeroed location for {obj.name}")

        # Calculate final scale factor but DON'T apply it to mesh data
        # This avoids memory-intensive vertex transformations
        final_scale_factor = scene_props.mesh_export_scale
        if scene_props.mesh_export_units == "CENTIMETERS":
            # Apply 100x scale for Meters (Blender default) 
            # to Centimeters (UE default)
            final_scale_factor *= 100.0 
            logger.info(f"Export scale factor: {final_scale_factor:.2f} (includes M to CM conversion)")
        else:
            logger.info(f"Export scale factor: {final_scale_factor:.2f}")

        # For GLTF and USD, we don't support scaling to avoid crashes
        if scene_props.mesh_export_format in ["GLTF", "USD"]:
            if abs(final_scale_factor - 1.0) > 1e-6:
                logger.info(f"Scale will be ignored for {scene_props.mesh_export_format} format")
            final_scale_factor = 1.0

        # Only apply rotation transform - scale will be passed to exporters
        apply_transforms(obj, apply_rotation=True, apply_scale=False)

        return obj.name, base_name, final_scale_factor
    except Exception as e:
        raise RuntimeError(
            f"Failed to setup (rename/zero) {obj.name}: {e}"
        ) from e
    

def apply_transforms(obj, apply_location=False, 
                     apply_rotation=False, apply_scale=False):
    """
    Applies specified transforms to the object.

    Args:
        obj (bpy.types.Object): The object to apply transforms to.
        apply_location (bool): Whether to apply location transforms.
        apply_rotation (bool): Whether to apply rotation transforms.
        apply_scale (bool): Whether to apply scale transforms.

    Returns:
        None
    """
    if not obj:
        logger.warning("Attempted to apply transforms to an invalid object.")
        return
    if not (apply_location or apply_rotation or apply_scale):
        logger.info(f"No transforms requested for {obj.name}. Skipping apply.")
        return

    transforms_to_apply = []
    if apply_location: 
        transforms_to_apply.append("location")
    if apply_rotation: 
        transforms_to_apply.append("rotation")
    if apply_scale: 
        transforms_to_apply.append("scale")

    logger.info(f"Applying {', '.join(transforms_to_apply)} "
                f"transforms for {obj.name}...")
    try:
        with bpy.context.temp_override(
            selected_editable_objects=[obj],
            selected_objects=[obj], active_object=obj):
            bpy.ops.object.transform_apply(location=apply_location,
                                           rotation=apply_rotation,
                                           scale=apply_scale)
        logger.info(f"Successfully applied {', '.join(transforms_to_apply)} "
                    f"for {obj.name}")
    except Exception as e:
        logger.error(f"Failed to apply transforms for {obj.name}: {e}")
        raise


def apply_mesh_modifiers(obj, modifier_mode="VISIBLE"):
    """
    Apply modifiers on a mesh object based on the specified mode.
    
    Args:
        obj (bpy.types.Object): The object whose modifiers to apply.
        modifier_mode (str): Which modifiers to apply ("NONE", "VISIBLE", "RENDER").
        
    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    
    # Skip all modifier application if mode is NONE
    if modifier_mode == "NONE":
        logger.info(f"Skipping modifier application for {obj.name} (mode: NONE)")
        return
        
    logger.info(f"Applying {modifier_mode.lower()} modifiers for {obj.name}...")
    current_mode = obj.mode
    MeshOperations.safe_mode_set(obj, "OBJECT")

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]
    applied_modifiers = []
    poly_count = len(obj.data.polygons)
    is_large_mesh = poly_count > LARGE_MESH_THRESHOLD

    try:
        for modifier in obj.modifiers[:]:  # Iterate over a copy
            should_apply = False
            
            # Determine if we should apply this modifier based on mode
            if modifier_mode == "VISIBLE":
                should_apply = modifier.show_viewport
            elif modifier_mode == "RENDER":
                should_apply = modifier.show_render
                
            if should_apply:
                mod_name = modifier.name
                logger.info(f"Applying modifier: {mod_name} ({modifier_mode.lower()})")
                try:
                    with bpy.context.temp_override(**override):
                        bpy.ops.object.modifier_apply(modifier=mod_name)
                    applied_modifiers.append(mod_name)
                    
                    # Memory cleanup for large meshes after every 3 modifiers
                    if is_large_mesh and len(applied_modifiers) % 3 == 0:
                        MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)
                        logger.info(f"Memory cleanup after {len(applied_modifiers)} modifiers")
                        
                except (RuntimeError, ReferenceError) as e:
                    logger.warning(
                        f"Could not apply modifier '{mod_name}' "
                        f"on {obj.name}: {e}"
                    )
            else:
                status = "viewport disabled" if modifier_mode == "VISIBLE" else "render disabled"
                logger.info(f"Skipping modifier '{modifier.name}': {status}")
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)
    logger.info(
        f"Finished applying modifiers. Applied: {applied_modifiers}"
    )


def compress_textures(obj, ratio, export_path=None, save_compressed=True):
    """
    Compresses textures based on decimation ratio with no user input required.
    
    Args:
        obj:    The mesh object whose textures should be compressed
        ratio:  The decimation ratio 
                1.0 = full quality, 0.01 = heavy decimation
        export_path: Directory to save compressed textures to
        save_compressed: Whether to save compressed textures to disk
        
    Returns:
        List of modified image names for reporting
    """
    if not obj or obj.type != "MESH":
        return []
    
    logger.info(f"Compressing textures for {obj.name} "
                f"(decimation ratio: {ratio:.3f})...")
    
    # Get all materials on the object
    materials = obj.data.materials
    if not materials:
        logger.info(f"No materials found on {obj.name}, "
                    f"skipping texture compression")
        return []
    
    logger.info(f"Found {len(materials)} materials on {obj.name}")
    
    modified_images = []
    
    # First pass - collect all unique images and nodes using them
    image_nodes = {}  # {image: [nodes using this image]}
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
            
        # Find all image texture nodes in the material
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                if node.image not in image_nodes:
                    image_nodes[node.image] = []
                image_nodes[node.image].append((mat, node))
    
    # Nothing to do if no images found
    if not image_nodes:
        logger.info(f"No texture images found on {obj.name}")
        return []
    
    logger.info(f"Found {len(image_nodes)} unique texture images to compress")
        
    # Calculate compression amount based on decimation ratio
    compression_factor = max(ratio**0.9, 0.05)  # Limit max compression to 1/20
    min_dimension = 64  # Minimum texture size
    
    # Process each image
    for orig_img, nodes_using_img in image_nodes.items():
        try:
            # Skip packed, or invalid images
            if (not orig_img.has_data 
                or orig_img.size[0] == 0 
                or orig_img.size[1] == 0):
                logger.debug(f"Skipping {orig_img.name}: invalid or no data")
                continue
                
            # Skip already compressed images (but allow recompression if different ratio)
            if orig_img.name.endswith("_LOD"):
                logger.debug(f"Skipping {orig_img.name}: already compressed")
                continue
                
            # Calculate new resolution
            orig_width, orig_height = orig_img.size
            is_power_of_2 = ((orig_width & (orig_width - 1) == 0) 
                             and (orig_height & (orig_height - 1) == 0))
            
            new_width = max(int(orig_width * compression_factor), min_dimension)
            new_height = max(int(orig_height * compression_factor), min_dimension)
            
            # Round to power of 2 if original was power of 2
            if is_power_of_2:
                new_width = 2 ** max(0, (new_width - 1).bit_length())
                new_height = 2 ** max(0, (new_height - 1).bit_length())
                
            # Skip if size hasn't changed
            if (new_width, new_height) == (orig_width, orig_height):
                continue
            
            # Create a copy of the original image with unique name based on ratio
            ratio_suffix = f"{int(ratio * 100):02d}"  # Convert 0.75 to "75"
            copy_name = f"{orig_img.name}_LOD{ratio_suffix}"
            
            # Check if copy already exists, reuse if it does
            copied_img = bpy.data.images.get(copy_name)
            if copied_img:
                # If dimensions don't match our target, recreate it
                if (copied_img.size[0] != new_width 
                    or copied_img.size[1] != new_height):
                    bpy.data.images.remove(copied_img)
                    copied_img = None
            
            if not copied_img:
                # Create new image with proper dimensions
                copied_img = bpy.data.images.new(
                    name=copy_name,
                    width=new_width,
                    height=new_height,
                    alpha=True if hasattr(orig_img, 'alpha') and orig_img.alpha else False,
                    float_buffer=orig_img.is_float if hasattr(orig_img, 'is_float') else False
                )
                
                # Copy pixel data from original and resize using a more reliable method
                if orig_img.has_data and len(orig_img.pixels) > 0:
                    try:
                        # Ensure original image is loaded and packed
                        if not orig_img.packed_file and orig_img.filepath:
                            orig_img.reload()
                        
                        # Use a different approach: create at target size and use GPU for scaling
                        # First, save original to a temporary location if it has a filepath
                        import tempfile
                        
                        if orig_img.filepath and os.path.exists(bpy.path.abspath(orig_img.filepath)):
                            # Use the existing file
                            source_path = bpy.path.abspath(orig_img.filepath)
                            # Load the image into the new image and scale it
                            copied_img.filepath_raw = source_path
                            copied_img.reload()
                            
                            # Now scale to target size
                            copied_img.scale(new_width, new_height)
                        else:
                            # Image is procedural or packed, save it temporarily
                            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                            temp_file.close()
                            
                            with temporary_image_file(temp_file.name) as temp_path:
                                # Save the original image to temp file
                                orig_img.filepath_raw = temp_path
                                orig_img.file_format = 'PNG'
                                orig_img.save()
                                
                                # Load the image into the new image and scale it
                                copied_img.filepath_raw = temp_path
                                copied_img.reload()
                                
                                # Now scale to target size
                                copied_img.scale(new_width, new_height)
                        
                        # Copy other relevant properties
                        copied_img.colorspace_settings.name = (
                            orig_img.colorspace_settings.name
                        )
                        
                    except Exception as e:
                        logger.warning(f"Error copying pixels for "
                                       f"{orig_img.name}: {e}")
                        # Clean up failed copy
                        if copied_img:
                            bpy.data.images.remove(copied_img)
                        continue
                        
                logger.info(f"Created compressed copy of '{orig_img.name}' "
                            f"at {new_width}x{new_height} "
                            f"(compression factor: {compression_factor:.2f})")
                
                # Save compressed texture to disk if requested
                if save_compressed and export_path:
                    try:
                        # Determine file extension from original
                        orig_ext = ".jpg"  # Default
                        if orig_img.filepath:
                            orig_ext = os.path.splitext(orig_img.filepath)[1] or ".jpg"
                        elif "." in orig_img.name:
                            orig_ext = "." + orig_img.name.split(".")[-1]
                        
                        # Create compressed texture filename
                        base_name = os.path.splitext(orig_img.name)[0]
                        compressed_filename = f"{base_name}_LOD{ratio_suffix}{orig_ext}"
                        compressed_filepath = os.path.join(export_path, compressed_filename)
                        
                        # Save the compressed texture
                        copied_img.filepath_raw = compressed_filepath
                        copied_img.file_format = 'JPEG' if orig_ext.lower() in ['.jpg', '.jpeg'] else 'PNG'
                        copied_img.save()
                        
                        logger.info(f"Saved compressed texture: {compressed_filename}")
                        
                    except Exception as save_e:
                        logger.warning(f"Failed to save compressed texture {copy_name}: {save_e}")
            
            # Update material nodes to use the copied image
            for mat, node in nodes_using_img:
                node.image = copied_img
                logger.debug(f"Updated node '{node.name}' in material '{mat.name}' to use compressed image")
            
            modified_images.append(f"{orig_img.name} ({orig_width}x{orig_height} "
                                   f"→ {new_width}x{new_height})")
            
            # Store original image reference on the object for restoration
            if "original_textures" not in obj:
                obj["original_textures"] = {}
            
            obj["original_textures"][copy_name] = orig_img.name
            
        except Exception as e:
            logger.error(f"Error processing texture {orig_img.name}: {e}", exc_info=True)
            continue
    
    return modified_images


def restore_original_textures(obj):
    """
    Restores original textures after exportby replacing 
    compressed copies with originals.
    
    Args:
        obj (bpy.types.Object): The object whose textures to restore.
    
    Returns:
        None
    """
    if not obj or obj.type != "MESH" or "original_textures" not in obj:
        return
    
    texture_map = obj.get("original_textures", {})
    if not texture_map:
        return
    
    logger.info(f"Restoring original textures for {obj.name}...")
    
    # Get all materials on the object
    materials = obj.data.materials
    if not materials:
        return
    
    # Find all image texture nodes and restore originals
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
            
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                # Check if this is an LOD image that needs restoration
                if node.image.name in texture_map:
                    original_name = texture_map[node.image.name]
                    original_img = bpy.data.images.get(original_name)
                    
                    if original_img:
                        logger.info(f"Restoring {node.image.name} "
                                    f"→ {original_name}")
                        node.image = original_img
    
    # Clean up the mapping
    del obj["original_textures"]
    
    # Delete any unused LOD textures
    try:
        for img in list(bpy.data.images):  # Use list to avoid iteration issues
            if "_LOD" in img.name and img.users == 0:
                logger.debug(f"Removing unused LOD texture: {img.name}")
                bpy.data.images.remove(img)
    except Exception as e:
        logger.warning(f"Error cleaning up LOD textures: {e}")


def apply_decimate_modifier(obj, ratio, decimate_type, 
                            sym_axis="X", sym=False):
    """
    Adds, configures, and applies a Decimate modifier.
    
    Args:
        obj (bpy.types.Object): The object to apply the modifier to.
        ratio (float): The decimation ratio (0.0 to 1.0).
        decimate_type (str): The type of decimation to apply.
        sym_axis (str): The symmetry axis for decimation.
        sym (bool): Whether to apply symmetry.

    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    
    # Get initial poly count for logging
    initial_poly_count = len(obj.data.polygons)
    logger.info(
        f"Applying Decimate to mesh with {initial_poly_count:,} polygons "
        f"(Ratio: {ratio:.3f}, Type: {decimate_type})..."
    )
    
    # Memory optimisation for very large meshes before decimation
    if initial_poly_count > VERY_LARGE_MESH_THRESHOLD:
        logger.info("Very large mesh detected, enabling memory optimisation")
        MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)

    current_mode = obj.mode
    MeshOperations.safe_mode_set(obj, "OBJECT")

    # Skip the old texture compression system - we now use simple external texture saving
    compressed_texture_list = []
    # Texture compression disabled - using simple external texture saving instead
    logger.debug("Skipping texture compression - using external texture saving")

    # Create and apply decimate modifier
    mod_name = "TempDecimate"
    dec_mod = obj.modifiers.new(name=mod_name, type="DECIMATE")
    dec_mod.decimate_type = decimate_type.upper()

    # Right now it only supports COLLAPSE
    if dec_mod.decimate_type == "COLLAPSE":
        dec_mod.ratio = ratio
        # Set use_symmetry first
        dec_mod.use_symmetry = sym
        # Only set the axis if symmetry is enabled
        if sym:
            # Ensure axis is valid before setting
            axis_upper = sym_axis.upper()
            if axis_upper not in {'X', 'Y', 'Z'}:
                 logger.error(f"Invalid symmetry axis value received: "
                              f"{sym_axis}. Aborting modifier application.")
                 obj.modifiers.remove(dec_mod) # Clean up modifier
                 raise ValueError(f"Invalid symmetry axis: {sym_axis}")

            dec_mod.symmetry_axis = axis_upper
            logger.info(
                f"Using symmetry axis: {axis_upper}"
            )

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=mod_name)
        
        # Log final results
        final_poly_count = len(obj.data.polygons)
        actual_ratio = (final_poly_count / initial_poly_count 
                        if initial_poly_count > 0 else 0)
        logger.info(
            f"Decimation complete: {initial_poly_count} "
            f"→ {final_poly_count} polys "
            f"(target: {ratio:.3f}, actual: {actual_ratio:.3f})"
        )
        
        # No texture compression details to log
        pass
            
    except Exception as e:
        logger.error(f"Failed to apply Decimate modifier: {e}")
        if mod_name in obj.modifiers:
            try:
                obj.modifiers.remove(dec_mod)
            except (ReferenceError, RuntimeError):
                 pass # Modifier already gone or object invalid
        raise RuntimeError(f"Failed to apply Decimate modifier: {e}") from e
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)


def triangulate_mesh(obj, method="BEAUTY", keep_normals=True):
    """
    Add and apply a triangulate modifier.
    
    Args:
        obj (bpy.types.Object): The object to triangulate.
        method (str): The triangulation method to use.
        keep_normals (bool): Whether to keep custom normals.
    
    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    
    poly_count = len(obj.data.polygons)
    logger.info(f"Triangulating {obj.name} with {poly_count:,} polygons...")
    
    # Memory optimisation for large meshes before triangulation
    if poly_count > LARGE_MESH_THRESHOLD:
        MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)
    
    current_mode = obj.mode
    MeshOperations.safe_mode_set(obj, "OBJECT")

    mod_name = "TempTriangulate"
    tri_mod = obj.modifiers.new(name=mod_name, type="TRIANGULATE")
    tri_mod.quad_method = method
    tri_mod.keep_custom_normals = keep_normals

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=mod_name)
        logger.info("Successfully triangulated.")
    except Exception as e:
        logger.warning(
            f"Could not apply triangulation modifier on {obj.name}: {e}"
        )
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)


def is_normal_map(node, img):
    """
    Detect if a texture is likely a normal map based on various indicators.
    
    Args:
        node: The image texture node
        img: The image data
    
    Returns:
        bool: True if likely a normal map
    """
    # Check node name
    node_name_lower = node.name.lower()
    if any(term in node_name_lower for term in ['normal', 'norm', 'nrm', 'bump']):
        return True
    
    # Check image name
    img_name_lower = img.name.lower()
    if any(term in img_name_lower for term in ['normal', 'norm', 'nrm', 'bump', '_n.', '_n_']):
        return True
    
    # Check if connected to Normal input
    for output in node.outputs:
        for link in output.links:
            if link.to_socket.name.lower() in ['normal', 'normal map']:
                return True
    
    # Check colorspace - normal maps are usually Non-Color
    if hasattr(img.colorspace_settings, 'name'):
        if img.colorspace_settings.name in ['Non-Color', 'Linear', 'Raw']:
            # Additional check - if it's connected to Base Color, it's not a normal map
            for output in node.outputs:
                for link in output.links:
                    if link.to_socket.name in ['Base Color', 'Color']:
                        return False
            return True
    
    return False


def get_texture_format_info(img):
    """
    Determine the best format to save a texture based on its properties.
    
    Args:
        img: The image data
    
    Returns:
        tuple: (format_string, has_alpha, is_hdr)
    """
    has_alpha = False
    is_hdr = False
    format_string = 'JPEG'
    
    # Check if image has alpha
    if hasattr(img, 'depth'):
        has_alpha = img.depth == 32  # RGBA
    elif hasattr(img, 'channels'):
        has_alpha = img.channels == 4
    
    # Check if HDR
    if hasattr(img, 'is_float'):
        is_hdr = img.is_float
    
    # Determine format based on properties
    if is_hdr:
        format_string = 'HDR'
    elif has_alpha:
        format_string = 'PNG'
    else:
        # Check original format
        if img.filepath:
            ext = os.path.splitext(img.filepath)[1].lower()
            if ext in ['.png']:
                format_string = 'PNG'
            elif ext in ['.tga', '.targa']:
                format_string = 'TARGA'
            elif ext in ['.exr']:
                format_string = 'OPEN_EXR'
    
    return format_string, has_alpha, is_hdr


def save_external_textures(obj, export_dir, lod_suffix="", resize_textures=True, scene_props=None):
    """
    Save textures used by the object to external files with LOD-appropriate sizes.
    Also updates material nodes to reference the external files for proper FBX export.
    
    Args:
        obj: The mesh object
        export_dir: Directory to save textures to
        lod_suffix: Suffix to add to texture names (e.g., "_LOD01")
        resize_textures: Whether to resize textures for LODs
        scene_props: Scene properties for texture settings
    
    Returns:
        Tuple: (List of saved texture filenames, Dict of original node references for restoration)
    """
    if not obj or obj.type != "MESH":
        return [], {}
    
    saved_textures = []
    original_references = {}  # Store original image references for restoration
    materials = obj.data.materials
    
    if not materials:
        return saved_textures, original_references
    
    # Determine target texture size based on LOD level (only if resizing is enabled)
    target_size = None
    if resize_textures and scene_props:
        if "LOD00" in lod_suffix:
            target_size = None  # Original size
        elif "LOD01" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod1_texture_size)
        elif "LOD02" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod2_texture_size)
        elif "LOD03" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod3_texture_size)
        elif "LOD04" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod4_texture_size)
        else:
            target_size = None  # Default to original
    
    logger.info(f"Target texture size for {lod_suffix}: {target_size or 'original'}")
    
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
            
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                img = node.image
                
                # Skip if no data
                if not img.has_data:
                    continue
                
                # Detect texture type
                is_normal = is_normal_map(node, img)
                
                # Get format info
                format_string, has_alpha, is_hdr = get_texture_format_info(img)
                
                # Determine file extension based on format
                ext_map = {
                    'JPEG': '.jpg',
                    'PNG': '.png',
                    'TARGA': '.tga',
                    'HDR': '.hdr',
                    'OPEN_EXR': '.exr'
                }
                ext = ext_map.get(format_string, '.jpg')
                
                # Create external filename
                base_name = os.path.splitext(img.name)[0]
                external_filename = f"{base_name}{lod_suffix}{ext}"
                external_path = os.path.join(export_dir, external_filename)
                
                try:
                    # Ensure the image has data loaded
                    if not img.has_data and img.filepath:
                        img.reload()
                    
                    # Save a copy of the image (with resizing if needed)
                    if img.has_data:
                        img_to_save = img
                        temp_img = None
                        
                        # Check if we need to resize
                        orig_width, orig_height = img.size
                        
                        # Adjust target size for normal maps if preservation is enabled
                        adjusted_target_size = target_size
                        if is_normal and scene_props and scene_props.mesh_export_preserve_normal_maps and target_size:
                            # Keep normal maps at one LOD level higher
                            if "LOD02" in lod_suffix:
                                adjusted_target_size = int(scene_props.mesh_export_lod1_texture_size)
                            elif "LOD03" in lod_suffix:
                                adjusted_target_size = int(scene_props.mesh_export_lod2_texture_size)
                            elif "LOD04" in lod_suffix:
                                adjusted_target_size = int(scene_props.mesh_export_lod3_texture_size)
                            logger.info(f"Preserving normal map quality: {target_size} → {adjusted_target_size}")
                        
                        # Only resize if image is larger than target (no upscaling)
                        needs_resize = (adjusted_target_size is not None and 
                                      (orig_width > adjusted_target_size or orig_height > adjusted_target_size))
                        
                        if needs_resize:
                            # Calculate new dimensions preserving aspect ratio
                            aspect_ratio = orig_width / orig_height
                            
                            if orig_width > orig_height:
                                new_width = adjusted_target_size
                                new_height = int(adjusted_target_size / aspect_ratio)
                            else:
                                new_height = adjusted_target_size
                                new_width = int(adjusted_target_size * aspect_ratio)
                            
                            # Ensure dimensions are at least 1
                            new_width = max(1, new_width)
                            new_height = max(1, new_height)
                            
                            logger.info(f"Resizing {img.name} from {orig_width}x{orig_height} to {new_width}x{new_height}")
                            
                            # Create a temporary resized copy
                            temp_img = img.copy()
                            temp_img.name = f"{img.name}_temp_resize"
                            
                            # Scale the temporary image
                            temp_img.scale(new_width, new_height)
                            img_to_save = temp_img
                        else:
                            if adjusted_target_size is not None:
                                logger.info(f"Skipping resize for {img.name} ({orig_width}x{orig_height}) - already smaller than target")
                        
                        # Set the save path and format
                        original_filepath = img_to_save.filepath_raw
                        img_to_save.filepath_raw = external_path
                        img_to_save.file_format = format_string
                        
                        # Set JPEG quality if applicable
                        if format_string == 'JPEG' and scene_props:
                            # Note: Blender's save_render settings affect image saving
                            scene = bpy.context.scene
                            original_quality = scene.render.image_settings.quality
                            scene.render.image_settings.quality = scene_props.mesh_export_texture_quality
                        
                        # Save the image
                        img_to_save.save()
                        
                        # Restore JPEG quality
                        if format_string == 'JPEG' and scene_props:
                            scene.render.image_settings.quality = original_quality
                        
                        # Restore original filepath to avoid affecting the scene
                        img_to_save.filepath_raw = original_filepath
                        
                        # Clean up temporary image
                        if temp_img:
                            bpy.data.images.remove(temp_img)
                        
                        # Create a new image that references the external file
                        external_img = bpy.data.images.load(external_path)
                        external_img.name = f"{img.name}_external"
                        
                        # Preserve colorspace settings
                        if hasattr(img, 'colorspace_settings'):
                            external_img.colorspace_settings.name = img.colorspace_settings.name
                        
                        # Store original reference for restoration
                        original_references[node] = img
                        
                        # Update the material node to use the external image
                        node.image = external_img
                        
                        saved_textures.append(external_filename)
                        size_info = f"{orig_width}x{orig_height}"
                        if needs_resize:
                            size_info += f" → {new_width}x{new_height}"
                        texture_type = "normal map" if is_normal else "texture"
                        logger.info(f"Saved external {texture_type}: {external_filename} ({size_info}, {format_string})")
                    else:
                        logger.warning(f"Image {img.name} has no data to save")
                    
                except Exception as e:
                    logger.warning(f"Failed to save texture {img.name}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
    
    return saved_textures, original_references


def restore_material_references(original_references):
    """
    Restore original material node references and clean up external image references.
    
    Args:
        original_references: Dict mapping nodes to their original images
    """
    for node, original_img in original_references.items():
        try:
            # Get the external image we created
            external_img = node.image
            
            # Restore original image reference
            node.image = original_img
            
            # Remove the external image from Blender data
            if external_img and external_img.name.endswith("_external"):
                try:
                    bpy.data.images.remove(external_img)
                    logger.debug(f"Cleaned up external image reference: {external_img.name}")
                except ReferenceError:
                    # Image was already removed, which is fine
                    logger.debug(f"External image already cleaned up: {external_img.name}")
                
        except (ReferenceError, AttributeError):
            # Node or image was already removed, which can happen during cleanup
            logger.debug("Material reference already cleaned up")
        except Exception as e:
            logger.warning(f"Error restoring material reference: {e}")


def export_object(obj, file_path, scene_props, export_scale=1.0):
    """
    Exports a single object using scene properties.
    
    Args:
        obj (bpy.types.Object): The object to export.
        file_path (str): The file path for the export.
        scene_props (bpy.types.PropertyGroup): Scene properties for export.
        export_scale (float): Scale factor to apply during export.
    
    Returns:
        bool: True if export was successful, False otherwise.
    """
    fmt = scene_props.mesh_export_format
    success = False
    # base_file_path = os.path.splitext(file_path)[0] # Ensure no extension yet
    base_file_path = file_path
    
    # Handle GLTF format extensions
    if fmt == "GLTF":
        if scene_props.mesh_export_gltf_type == "GLB":
            export_filepath = f"{base_file_path}.glb"
        else:
            export_filepath = f"{base_file_path}.gltf"
    else:
        export_filepath = f"{base_file_path}.{fmt.lower()}"

    temp_lod_lvl = obj.name.split("_")[-1]

    if temp_lod_lvl == "LOD01":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_01 * 100)
        downscale_size = "2048"
    elif temp_lod_lvl == "LOD02":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_02 * 100)
        downscale_size = "1024"
    elif temp_lod_lvl == "LOD03":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_03 * 100)
        downscale_size = "512"
    elif temp_lod_lvl == "LOD04":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_04 * 100)
        downscale_size = "256"
    else:
        export_quality = 100
        downscale_size = "KEEP"

    # Check mesh size and optimise if needed
    mesh_size = len(obj.data.polygons) if obj.data else 0
    if mesh_size > LARGE_MESH_THRESHOLD:
        logger.info(f"Large mesh export: {mesh_size:,} polygons")
        MeshOperations.update_mesh_data(obj, with_memory_cleanup=True)
        MeshOperations.update_view_layer()
    
    # Save external textures if not embedding
    external_textures = []
    original_references = {}
    if not scene_props.mesh_export_embed_textures:
        export_dir = os.path.dirname(export_filepath)
        lod_suffix = ""
        
        # Extract LOD suffix from object name if present
        if "_LOD" in obj.name:
            lod_part = obj.name.split("_LOD")[-1]
            if len(lod_part) == 2 and lod_part.isdigit():
                lod_suffix = f"_LOD{lod_part}"
        
        external_textures, original_references = save_external_textures(obj, export_dir, lod_suffix, scene_props.mesh_export_resize_textures, scene_props)
    
    logger.info(
        f"Exporting {os.path.basename(export_filepath)} ({fmt}) - {mesh_size:,} polygons..."
    )

    # Convert axis values for OBJ and STL export
    def convert_axis_for_export(axis_value):
        """Convert axis values like '-Z' to 'NEGATIVE_Z' for OBJ/STL export."""
        if axis_value.startswith('-'):
            return f"NEGATIVE_{axis_value[1]}"
        return axis_value

    with temp_selection_context(bpy.context, active_object=obj,
                                selected_objects=[obj]):
        try:
            if fmt == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath=export_filepath,
                    use_selection=True,
                    global_scale=export_scale, # Pass scale to exporter instead of applying to mesh
                    axis_forward=scene_props.mesh_export_coord_forward,
                    axis_up=scene_props.mesh_export_coord_up,
                    apply_unit_scale=False,
                    apply_scale_options="FBX_SCALE_ALL",
                    object_types={"MESH"},
                    path_mode="STRIP" if not scene_props.mesh_export_embed_textures else "COPY",
                    embed_textures=scene_props.mesh_export_embed_textures,
                    mesh_smooth_type=scene_props.mesh_export_smoothing,
                    use_mesh_modifiers=False, # Handled by apply_mesh_modifiers
                    use_triangles=False,      # Handled by triangulate_mesh
                )
            elif fmt == "OBJ":
                bpy.ops.wm.obj_export(
                    filepath=export_filepath,
                    export_selected_objects=True,
                    global_scale=export_scale, # Pass scale to exporter instead of applying to mesh
                    forward_axis=convert_axis_for_export(scene_props.mesh_export_coord_forward),
                    up_axis=convert_axis_for_export(scene_props.mesh_export_coord_up),
                    export_materials=True,
                    path_mode="STRIP",  # OBJ doesn't embed textures
                    export_normals=True,
                    export_smooth_groups=True,
                    apply_modifiers=False, # Handled by apply_mesh_modifiers
                    export_triangulated_mesh=False, # Handled triangulate_mesh
                )
            elif fmt == "GLTF":
                # GLTF doesn't support global scale - warn if scale is not 1.0
                if abs(export_scale - 1.0) > 1e-6:
                    logger.warning(f"Scale {export_scale} will NOT be applied for GLTF export (format limitation). "
                                 f"Export at original size or apply scale manually before export.")
                
                # For GLTF, textures are always embedded in GLB or copied with GLTF
                bpy.ops.export_scene.gltf(
                    filepath=export_filepath,
                    use_selection=True,
                    export_format=scene_props.mesh_export_gltf_type,
                    export_apply=False, # Transforms/Mods applied manually
                    export_texcoords=True, # Explicitly export UVs
                    export_normals=True,
                    export_tangents=False, 
                    export_materials=scene_props.mesh_export_gltf_materials, 
                    export_vertex_color="MATERIAL", 
                    export_cameras=False,
                    export_lights=False,
                    export_skins=False,  # Disable skin export to reduce size
                    export_animations=False,  # Disable animation export to reduce size
                    export_extras=False,  # Disable extras to reduce size
                    export_yup=True, # Use Y-Up coordinate system
                    # Texture settings
                    export_texture_dir="",  # Export textures to same directory as GLTF
                    export_jpeg_quality=export_quality,
                    export_image_quality=export_quality,
                    export_def_bones=False, # Don't export bones
                    # Enable Draco compression for geometry based on user setting
                    export_draco_mesh_compression_enable=scene_props.mesh_export_use_draco_compression,
                    export_draco_mesh_compression_level=6,
                    export_draco_position_quantization=14,
                    export_draco_normal_quantization=10,
                    export_draco_texcoord_quantization=12,
                )
            elif fmt == "USD":
                # USD doesn't support global scale - warn if scale is not 1.0
                if abs(export_scale - 1.0) > 1e-6:
                    logger.warning(f"Scale {export_scale} will NOT be applied for USD export (format limitation). "
                                 f"Export at original size or apply scale manually before export.")
                
                bpy.ops.wm.usd_export(
                    filepath=export_filepath,
                    selected_objects_only=True,
                    export_global_forward_selection=(
                        convert_axis_for_export(scene_props.mesh_export_coord_forward)),
                    export_global_up_selection=(
                        convert_axis_for_export(scene_props.mesh_export_coord_up)),
                    export_meshes=True,
                    export_materials=True,
                    export_normals=True,
                    generate_preview_surface=False,
                    use_instancing=False,
                    evaluation_mode="RENDER",
                    triangulate_meshes=False, # Handled by triangulate_mesh
                    # Need to add a prop to track material quality
                    usdz_downscale_size=downscale_size,
                    export_textures=True,
                    export_textures_mode="NEW",
                    overwrite_textures=True,
                )
            elif fmt == "STL":
                bpy.ops.wm.stl_export(
                    filepath=export_filepath,
                    export_selected_objects=True,
                    global_scale=export_scale, # Pass scale to exporter instead of applying to mesh
                    forward_axis=convert_axis_for_export(scene_props.mesh_export_coord_forward),
                    up_axis=convert_axis_for_export(scene_props.mesh_export_coord_up),
                    apply_modifiers=False, # Handled by apply_mesh_modifiers
                )
            else:
                logger.error(f"Unsupported export format '{fmt}'")
                return False

            # Get file size
            file_size = os.path.getsize(export_filepath)
            file_size_mb = file_size / (1024 * 1024)
            
            # Calculate approximate size breakdown for GLTF/GLB
            size_info = f"Size: {file_size_mb:.2f} MB"
            
            # Add external texture info if any were saved
            if external_textures:
                export_dir = os.path.dirname(export_filepath)
                total_texture_size = 0
                
                for tex_filename in external_textures:
                    tex_path = os.path.join(export_dir, tex_filename)
                    try:
                        total_texture_size += os.path.getsize(tex_path)
                    except OSError:
                        pass
                
                if total_texture_size > 0:
                    texture_size_mb = total_texture_size / (1024 * 1024)
                    size_info += f" + {len(external_textures)} texture(s): {texture_size_mb:.2f} MB"
                    size_info += f" (Total: {file_size_mb + texture_size_mb:.2f} MB)"
            
            # For GLTF JSON format, also check for other texture files
            elif fmt == "GLTF" and scene_props.mesh_export_gltf_type == "GLTF_SEPARATE":
                export_dir = os.path.dirname(export_filepath)
                texture_files = []
                total_texture_size = 0
                
                # Look for common image formats in the same directory
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    pattern = os.path.join(export_dir, f"*{ext}")
                    import glob
                    texture_files.extend(glob.glob(pattern))
                
                if texture_files:
                    for tex_file in texture_files:
                        try:
                            total_texture_size += os.path.getsize(tex_file)
                        except OSError:
                            pass
                    
                    texture_size_mb = total_texture_size / (1024 * 1024)
                    size_info += f" + {len(texture_files)} texture(s): {texture_size_mb:.2f} MB"
                    size_info += f" (Total: {file_size_mb + texture_size_mb:.2f} MB)"
            
            elif fmt == "GLTF" and scene_props.mesh_export_gltf_type == "GLB":
                # Rough estimate: with compression, ~100 bytes per triangle
                estimated_mesh_size_mb = (mesh_size * 100) / (1024 * 1024)
                estimated_texture_size_mb = file_size_mb - estimated_mesh_size_mb
                if estimated_texture_size_mb > 0:
                    size_info += f" (est. mesh: {estimated_mesh_size_mb:.1f} MB, textures: {estimated_texture_size_mb:.1f} MB)"
            
            logger.info(
                f"Successfully exported {os.path.basename(export_filepath)} "
                f"({size_info})"
            )
            success = True
        except Exception as e:
            logger.error(
                f"Failed exporting {obj.name} as {fmt}: {e}", exc_info=True
            )
            success = False
        finally:
            # Restore original material references if we modified them
            if original_references:
                restore_material_references(original_references)
                logger.debug("Restored original material references")
    
    return success


def calculate_progressive_ratio(target_ratio, previous_ratio):
    """
    Calculate the decimation ratio needed to go from previous LOD to target LOD.
    
    Args:
        target_ratio (float): The target ratio from the original mesh (e.g., 0.5 for 50%)
        previous_ratio (float): The ratio of the previous LOD from original (e.g., 0.75 for 75%)
    
    Returns:
        float: The ratio to apply to get from previous LOD to target LOD
    """
    if previous_ratio <= 0:
        return target_ratio
    return target_ratio / previous_ratio


def cleanup_object(obj, obj_name_for_log):
    """
    Removes the specified object, handling potential errors.
    
    Args:
        obj (bpy.types.Object): The object to clean up.
        obj_name_for_log (str): The name to log for the object.
    
    Returns:
        None
    """
    if not obj:
        return
    log_name = obj_name_for_log if obj_name_for_log else "unnamed object"
    logger.info(f"Attempting cleanup for: {log_name}")
    
    # No texture restoration needed with the new simple system
    pass
    
    # Then remove the object
    try:
        mesh_data = obj.data # Store reference before removing object
        num_users = mesh_data.users
        poly_count = len(mesh_data.polygons) if mesh_data else 0
        was_large_mesh = poly_count > LARGE_MESH_THRESHOLD
        
        bpy.data.objects.remove(obj, do_unlink=True)
        logger.info(f"Cleaned up object: {log_name}")
        
        # If the mesh data had only this object as a user, remove it too
        if num_users == 1 and mesh_data:
             try:
                 # Clear geometry data for large meshes to free memory immediately
                 if was_large_mesh and hasattr(mesh_data, 'clear_geometry'):
                     mesh_data.clear_geometry()
                 bpy.data.meshes.remove(mesh_data)
                 logger.info(f"Cleaned up orphaned mesh data for: {log_name}")
             except (ReferenceError, Exception) as mesh_remove_e:
                 logger.warning(f"Issue removing mesh data for {log_name}: "
                                f"{mesh_remove_e}")
        
        # Force garbage collection for large meshes
        if was_large_mesh:
            MemoryManager.request_cleanup(force=True)
            logger.info(f"Memory cleanup completed for large mesh: {log_name}")

    except (ReferenceError, Exception) as remove_e:
        logger.warning(f"Issue during cleanup of {log_name}: {remove_e}")


# --- Operators ---

class MESH_OT_batch_export(Operator):
    """Exports selected mesh objects sequentially with status bar progress."""
    bl_idname = "mesh.batch_export"
    bl_label = "Export Selected Meshes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        """Enable only if mesh, curve, or metaball objects are selected."""
        return any(obj.type in ["MESH", "CURVE", "META"] for obj in context.selected_objects)

    def _validate_export_setup(self, context):
        """Validate objects and export path before processing.
        
        Returns:
            tuple: (objects_to_export, export_base_path, collections_to_export)
            
        Raises:
            ValidationError: If validation fails
        """
        scene_props = context.scene.mesh_exporter
        # Get selected objects for export
        objects_to_export = [
            obj for obj in context.selected_objects if obj.type in ["MESH", "CURVE", "META"]
        ]
        
        if not objects_to_export:
            raise ValidationError("No mesh, curve, or metaball objects selected.")
        
        # Check if we're in LOD hierarchy mode
        hierarchy_mode = (scene_props.mesh_export_lod and 
                         scene_props.mesh_export_lod_hierarchy and 
                         scene_props.mesh_export_format == "FBX")
        
        # Validate export path
        if not scene_props.mesh_export_path.strip():
            raise ValidationError("Export path cannot be empty.")
            
        export_base_path = bpy.path.abspath(scene_props.mesh_export_path)
        
        # Check if path exists or can be created
        if not os.path.isdir(export_base_path):
            try:
                os.makedirs(export_base_path, exist_ok=True)
                logger.info(f"Created export directory: {export_base_path}")
            except OSError as e:
                raise ResourceError(
                    f"Cannot create export directory '{export_base_path}': {e}"
                ) from e
            except Exception as e:
                raise ResourceError(
                    f"Unexpected error creating export directory: {e}"
                ) from e
        
        # Check if directory is writable
        if not os.access(export_base_path, os.W_OK):
            raise ResourceError(f"Export directory is not writable: {export_base_path}")
                
        return objects_to_export, export_base_path, hierarchy_mode

    def _process_object_hierarchy_export(self, obj, context, scene_props, export_base_path):
        """Process individual object hierarchy export with LODs.
        
        Returns:
            tuple: (success_count, failed_list)
        """
        logger.info(f"Processing object '{obj.name}' for hierarchy export")
        successful_exports = 0
        failed_exports = []
        temp_metaball_mesh = None
        
        try:
            # Get LOD ratios
            lod_ratios_prop = [
                scene_props.mesh_export_lod_ratio_01,
                scene_props.mesh_export_lod_ratio_02,
                scene_props.mesh_export_lod_ratio_03,
                scene_props.mesh_export_lod_ratio_04,
            ]
            ratios = [1.0] + lod_ratios_prop[:scene_props.mesh_export_lod_count]
            
            # Create all LOD objects
            lod_objects = []
            base_lod_obj = None
            previous_ratio = 1.0
            
            for lod_level, target_ratio in enumerate(ratios):
                if lod_level == 0:
                    # LOD0: Create base copy with all processing
                    logger.info("Creating base LOD0...")
                    lod_obj, temp_metaball_mesh = create_export_copy(obj, context)
                    
                    # Setup object (naming, location, scale)
                    (lod_obj_name, base_name, export_scale) = setup_export_object(
                        lod_obj, obj.name, scene_props, lod_level
                    )
                    
                    # Apply modifiers if needed
                    apply_mesh_modifiers(lod_obj, scene_props.mesh_export_apply_modifiers)
                    
                    # Triangulate if needed
                    if scene_props.mesh_export_tri:
                        method = scene_props.mesh_export_tri_method
                        k_nrms = scene_props.mesh_export_keep_normals
                        triangulate_mesh(lod_obj, method, k_nrms)
                    
                    base_lod_obj = lod_obj
                else:
                    # LOD1+: Create copy and apply progressive decimation
                    logger.info(f"Creating LOD{lod_level} with ratio {target_ratio}...")
                    
                    # Create a copy of the base LOD
                    lod_obj = base_lod_obj.copy()
                    lod_obj.data = base_lod_obj.data.copy()
                    context.collection.objects.link(lod_obj)
                    
                    # Only rename for LOD level (scale/location already handled in LOD0)
                    # Note: We pass the original object name, not the LOD0's modified name
                    (lod_obj_name, _, _) = setup_export_object(
                        lod_obj, obj.name, scene_props, lod_level
                    )
                    
                    # Apply decimation
                    decimate_modifier = lod_obj.modifiers.new(name=f"Decimate_LOD{lod_level}", type="DECIMATE")
                    decimate_modifier.decimate_type = scene_props.mesh_export_lod_type
                    decimate_modifier.ratio = target_ratio
                    
                    if scene_props.mesh_export_lod_symmetry:
                        decimate_modifier.use_symmetry = True
                        decimate_modifier.symmetry_axis = scene_props.mesh_export_lod_symmetry_axis
                    
                    # Apply modifier
                    context.view_layer.objects.active = lod_obj
                    MeshOperations.safe_mode_set(lod_obj, "OBJECT")
                    bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)
                
                lod_objects.append(lod_obj)
                previous_ratio = target_ratio
            
            # Create hierarchy structure (base_lod_obj is LOD0, first in list)
            parent_empty = create_lod_hierarchy(lod_objects[0], lod_objects[1:], obj.name, context)
            
            # Export the hierarchy as FBX
            # Use base_name which includes prefix/suffix but not LOD suffix
            export_path = os.path.join(export_base_path, f"{base_name}_LODGroup.fbx")
            
            # Select all LOD objects and parent for export
            bpy.ops.object.select_all(action='DESELECT')
            parent_empty.select_set(True)
            for lod_obj in lod_objects:
                lod_obj.select_set(True)
            context.view_layer.objects.active = parent_empty
            
            # Export FBX with hierarchy
            try:
                bpy.ops.export_scene.fbx(
                    filepath=export_path,
                    use_selection=True,
                    global_scale=scene_props.mesh_export_scale,
                    apply_scale_options='FBX_SCALE_ALL',
                    axis_forward=scene_props.mesh_export_coord_forward,
                    axis_up=scene_props.mesh_export_coord_up,
                    use_mesh_modifiers=False,  # Already applied
                    mesh_smooth_type=scene_props.mesh_export_smoothing,
                    use_tspace=True,
                    path_mode='COPY' if scene_props.mesh_export_embed_textures else 'AUTO',
                    embed_textures=scene_props.mesh_export_embed_textures
                )
                successful_exports = len(lod_objects)  # All LODs including base
                logger.info(f"Successfully exported hierarchy to {export_path}")
            except Exception as e:
                failed_exports.append(f"{obj.name} (Export failed: {e})")
                logger.error(f"Failed to export hierarchy: {e}")
            
            # Clean up temporary objects
            bpy.data.objects.remove(parent_empty, do_unlink=True)
            for lod_obj in lod_objects:
                bpy.data.objects.remove(lod_obj, do_unlink=True)
            
            # Clean up temporary metaball mesh if it exists
            if temp_metaball_mesh:
                bpy.data.meshes.remove(temp_metaball_mesh, do_unlink=True)
            
        except Exception as e:
            logger.error(f"Failed to process object hierarchy: {e}")
            failed_exports.append(f"{obj.name} (Processing failed: {e})")
        
        return successful_exports, failed_exports
    
    def _process_lod_export(self, original_obj, context, scene_props, export_base_path):
        """Process LOD export for a single object.
        
        Returns:
            tuple: (success_count, failed_list)
        """
        logger.info(
            f"Generating {scene_props.mesh_export_lod_count + 1} LOD levels..."
        )
        
        # Get LOD ratios
        lod_ratios_prop = [
            scene_props.mesh_export_lod_ratio_01,
            scene_props.mesh_export_lod_ratio_02,
            scene_props.mesh_export_lod_ratio_03,
            scene_props.mesh_export_lod_ratio_04,
        ]
        ratios = [1.0] + lod_ratios_prop[:scene_props.mesh_export_lod_count]
        
        # Initialise tracking variables
        successful_exports = 0
        failed_exports = []
        base_lod_obj = None
        previous_ratio = 1.0
        temp_metaball_mesh = None
        
        try:
            for lod_level, target_ratio in enumerate(ratios):
                lod_obj = None
                lod_obj_name = None
                
                try:
                    if lod_level == 0:
                        # LOD0: Create base copy with modifiers applied
                        logger.info("Creating base LOD0...")
                        lod_obj, temp_metaball_mesh = create_export_copy(
                            original_obj, context
                        )
                        (lod_obj_name, _, export_scale) = setup_export_object(
                            lod_obj, original_obj.name, scene_props, lod_level
                        )
                        apply_mesh_modifiers(lod_obj, scene_props.mesh_export_apply_modifiers)
                        base_lod_obj = lod_obj
                    else:
                        # LOD1+: Reuse previous LOD with progressive decimation
                        if base_lod_obj is None:
                            raise RuntimeError("Base LOD object lost, cannot continue")
                        
                        logger.info(f"Building LOD{lod_level} from previous LOD...")
                        
                        # Calculate progressive ratio
                        progressive_ratio = calculate_progressive_ratio(
                            target_ratio, previous_ratio
                        )
                        logger.info(
                            f"Progressive decimation ratio: {progressive_ratio:.3f} "
                            f"(from {previous_ratio:.3f} to {target_ratio:.3f})"
                        )
                        
                        # Rename for current LOD
                        (lod_obj_name, _, export_scale) = setup_export_object(
                            base_lod_obj, original_obj.name, scene_props, lod_level
                        )
                        
                        # Apply progressive decimation
                        apply_decimate_modifier(
                            base_lod_obj, progressive_ratio,
                            scene_props.mesh_export_lod_type,
                            scene_props.mesh_export_lod_symmetry_axis,
                            scene_props.mesh_export_lod_symmetry,
                        )
                        lod_obj = base_lod_obj
                    
                    # Triangulate if needed (applies to all LODs)
                    if scene_props.mesh_export_tri and lod_level == 0:
                        method = scene_props.mesh_export_tri_method
                        k_nrms = scene_props.mesh_export_keep_normals
                        triangulate_mesh(lod_obj, method, k_nrms)
                    
                    # Export current LOD
                    lod_file_path = os.path.join(export_base_path, lod_obj_name)
                    if export_object(lod_obj, lod_file_path, scene_props, export_scale):
                        successful_exports += 1
                    else:
                        raise RuntimeError("Export func failed")
                    
                    # Update previous ratio for next iteration
                    previous_ratio = target_ratio
                    
                except Exception as lod_e:
                    log_name = (
                        lod_obj_name if lod_obj_name else
                        f"{original_obj.name}_LOD{lod_level:02d}"
                    )
                    logger.error(f"Failed processing {log_name}: {lod_e}")
                    failed_exports.append(f"{original_obj.name} (LOD{lod_level:02d})")
                    # Break the loop on error since subsequent LODs depend on previous
                    break
                    
        finally:
            # Cleanup resources
            if base_lod_obj:
                cleanup_object(base_lod_obj, "base_lod_object")
            if temp_metaball_mesh:
                cleanup_object(temp_metaball_mesh, "temp_metaball_mesh")
                
            # Memory cleanup for large meshes
            if (original_obj.type == "MESH" and 
                len(original_obj.data.polygons if original_obj.data else []) > LARGE_MESH_THRESHOLD):
                MemoryManager.request_cleanup()
                logger.debug("Memory cleanup after LOD level processing")
            
        return successful_exports, failed_exports

    def _process_single_export(self, original_obj, context, scene_props, export_base_path):
        """Process non-LOD export for a single object.
        
        Returns:
            tuple: (success_count, failed_list)
        """
        export_obj = None
        export_obj_name = None
        temp_metaball_mesh = None
        
        try:
            logger.info("Processing single export (no LODs)..")
            export_obj, temp_metaball_mesh = create_export_copy(
                original_obj, context
            )
            
            # Use context manager for the export object
            with temporary_object(export_obj, export_obj_name) as obj:
                (export_obj_name, base_name, export_scale) = setup_export_object(
                    obj, original_obj.name, scene_props
                )
                apply_mesh_modifiers(obj, scene_props.mesh_export_apply_modifiers)
                
                if scene_props.mesh_export_tri:
                    triangulate_mesh(
                        obj,
                        scene_props.mesh_export_tri_method,
                        scene_props.mesh_export_keep_normals
                    )
                
                file_path = os.path.join(export_base_path, base_name)
                if export_object(obj, file_path, scene_props, export_scale):
                    return 1, []
                else:
                    return 0, [original_obj.name]
                
        except Exception as e:
            log_name = export_obj_name if export_obj_name else original_obj.name
            logger.error(f"Failed processing {log_name}: {e}")
            return 0, [f"{original_obj.name} (Processing Error)"]
        finally:
            # Cleanup temp metaball mesh if exists
            if temp_metaball_mesh:
                cleanup_object(temp_metaball_mesh, "temp_metaball_mesh")

    def _generate_export_report(self, successful_exports, failed_exports, elapsed_time):
        """Generate final export report message.
        
        Returns:
            tuple: (message, report_type, overall_success)
        """
        overall_success = len(failed_exports) == 0
        message = (
            f"Export finished in {elapsed_time:.2f}s. "
            f"Exported {successful_exports} files."
        )
        
        if failed_exports:
            unique_fails = sorted(list(set(f.split(' (')[0] for f in failed_exports)))
            fail_summary = (
                f"Failed exports logged for: {len(unique_fails)} original "
                f"objects ({', '.join(unique_fails[:5])}"
                f"{'...' if len(unique_fails) > 5 else ''}). Check console/log."
            )
            message += f" {fail_summary}"
            logger.warning(f"Failures occurred for: {', '.join(unique_fails)}")
            
        report_type = {"INFO"} if overall_success else {"WARNING"}
        return message, report_type, overall_success

    def execute(self, context):
        """Runs the batch export process."""
        start_time = time.time()
        
        try:
            # Validate setup
            objects_to_export, export_base_path, hierarchy_mode = self._validate_export_setup(context)
        except ValidationError as e:
            self.report({"WARNING"}, str(e))
            logger.warning(f"Validation failed: {e}")
            return {"CANCELLED"}
        except ResourceError as e:
            self.report({"ERROR"}, str(e))
            logger.error(f"Resource error: {e}")
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Unexpected validation error: {e}")
            logger.error(f"Unexpected validation error: {e}", exc_info=True)
            return {"CANCELLED"}
        
        # Initialise tracking
        scene_props = context.scene.mesh_exporter
        wm = context.window_manager
        successful_exports = 0
        failed_exports = []
        
        # Get total items to process
        total_items = len(objects_to_export)
        if hierarchy_mode:
            logger.info(
                f"Starting batch export for {total_items} objects with LOD hierarchies to {export_base_path}"
            )
        else:
            logger.info(
                f"Starting batch export for {total_items} objects to {export_base_path}"
            )
        
        wm.progress_begin(0, total_items)
        try:
            # Process each object
            for index, original_obj in enumerate(objects_to_export):
                wm.progress_update(index + 1)
                logger.info(f"Processing ({index + 1}/{total_items}): {original_obj.name}")
                
                try:
                    # Process with hierarchy mode, regular LOD, or single export
                    if hierarchy_mode:
                        success_count, failures = self._process_object_hierarchy_export(
                            original_obj, context, scene_props, export_base_path
                        )
                    elif scene_props.mesh_export_lod:
                        success_count, failures = self._process_lod_export(
                            original_obj, context, scene_props, export_base_path
                        )
                    else:
                        success_count, failures = self._process_single_export(
                            original_obj, context, scene_props, export_base_path
                        )
                    
                    # Update tracking
                    successful_exports += success_count
                    failed_exports.extend(failures)
                    
                    # Mark object if successful
                    if not failures:
                        export_indicators.mark_object_as_exported(original_obj)
                        logger.info(f"Marked original {original_obj.name} as exported.")
                    else:
                        logger.info(f"Skipped marking {original_obj.name} due to errors.")
                        
                except ProcessingError as e:
                    logger.error(f"Processing error for {original_obj.name}: {e}")
                    failed_exports.append(f"{original_obj.name} (Processing Error)")
                except ResourceError as e:
                    logger.error(f"Resource error for {original_obj.name}: {e}")
                    failed_exports.append(f"{original_obj.name} (Resource Error)")
                except Exception as e:
                    logger.error(f"Unexpected error for {original_obj.name}: {e}", exc_info=True)
                    failed_exports.append(f"{original_obj.name} (Unexpected Error)")
                    
        except KeyboardInterrupt:
            logger.info("Export cancelled by user")
            self.report({"INFO"}, "Export cancelled by user")
            return {"CANCELLED"}
        except Exception as e:
            logger.error(f"Critical error during export: {e}", exc_info=True)
            self.report({"ERROR"}, f"Critical export error: {e}")
            return {"CANCELLED"}
        finally:
            wm.progress_end()
            # Ensure any pending memory cleanup is performed
            MemoryManager.cleanup_if_pending()
        
        # Generate and display report
        elapsed_time = time.time() - start_time
        message, report_type, overall_success = self._generate_export_report(
            successful_exports, failed_exports, elapsed_time
        )
        
        logger.log(logging.INFO if overall_success else logging.WARNING, message)
        self.report(report_type, message)
        
        # Trigger viewport redraw
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
        
        return {"FINISHED"}


class OBJECT_OT_select_by_name(Operator):
    """Selects and focuses on the specified object."""
    bl_idname = "object.select_by_name"
    bl_label = "Select Object by Name"
    bl_description = "Selects and focuses on the specified object"
    bl_options = {"REGISTER", "INTERNAL"}

    # Correct the property definition using annotation
    object_name: StringProperty()

    def execute(self, context):
        """Executes the selection using direct API."""
        # Access the property using self.object_name
        target_obj = bpy.data.objects.get(self.object_name)
        if not target_obj:
            logger.warning(f"Object '{self.object_name}' "
                           f"not found for selection.")
            return {"CANCELLED"}
        
        # Deselect all objects directly
        for obj in context.scene.objects:
            if obj.select_get():
                obj.select_set(False)
                
        # Select target and make it active
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj
        
        return {"FINISHED"}


# --- Registration ---
classes = (
    MESH_OT_batch_export,
    OBJECT_OT_select_by_name,
)


def register():
    """Registers operator classes."""
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            logger.warning(f"Class {cls.__name__} already registered.")
            pass  # Already registered


def unregister():
    """Unregisters operator classes."""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            logger.warning(f"Class {cls.__name__} already unregistered.")
            pass  # Already unregistered