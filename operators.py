import bpy
import os
from bpy.types import Operator

# Main export operator
class MESH_OT_batch_export(Operator):
    bl_idname = "mesh.batch_export"
    bl_label = "Export Selected Meshes"
    bl_description = "Export all selected objects as mesh files"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0
    
    def execute(self, context):
        scene = context.scene
        export_path = bpy.path.abspath(scene.mesh_export_path)
        lod_export = False
        
        # Create export directory if it doesn't exist
        if not os.path.exists(export_path):
            os.makedirs(export_path)
        
        selected_objects = context.selected_objects
        mesh_objects = [obj for obj in selected_objects if obj.type == "MESH"]
        
        if not mesh_objects:
            self.report({"WARNING"}, "No mesh objects selected")
            return {"CANCELLED"}
        
        # Store original state to restore later
        # original_scale = {}
        # for obj in mesh_objects:
        #     original_scale[obj.name] = obj.scale.copy()
            
            # Apply scale if needed
            # if scene.mesh_export_scale != 1.0:
            #     obj.scale *= scene.mesh_export_scale
        
        # Determine coordinate system for export
        if scene.mesh_export_axis_simple == "Godot":
            axis_forward_export = "Z"
            axis_up_export = "Y"
        elif scene.mesh_export_axis_simple == "Unity":
            axis_forward_export = "Z"
            axis_up_export = "Y"
        elif scene.mesh_export_axis_simple == "Unreal":
            axis_forward_export = "X"
            axis_up_export = "Z"
        else:   # default to Blender axis
            axis_forward_export ="Y"
            axis_up_export = "Z"
        
        # Export based on selected format
        format_type = scene.mesh_export_format
        
        for obj in mesh_objects:
            # Make this the only selected object
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            context.view_layer.objects.active = obj
            
            # Apply transforms if enabled
            # if scene.mesh_export_apply_location:
            #     bpy.ops.object.transform_apply(location=True)
            # if scene.mesh_export_apply_rotation:
            #     bpy.ops.object.transform_apply(rotation=True)
            # if scene.mesh_export_apply_scale:
            #     bpy.ops.object.transform_apply(scale=True)

            # Apply zero location if needed
            if scene.mesh_export_zero_location:
                original_location = obj.location.copy()
                obj.location = (0, 0, 0)
            
            file_name = scene.mesh_export_prefix + obj.name + scene.mesh_export_suffix
            file_path = os.path.join(export_path, file_name)
            
            if format_type == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath = file_path + ".fbx", 
                    use_selection = True,
                    axis_forward = axis_forward_export,
                    axis_up = axis_up_export,
                    use_mesh_modifiers = True,
                    use_triangles= scene.mesh_export_triangulate,
                )
            elif format_type == "OBJ":
                bpy.ops.export_scene.obj(
                    filepath = file_path + ".obj", 
                    use_selection = True,
                    axis_forward = axis_forward_export,
                    axis_up = axis_up_export,
                    use_mesh_modifiers = True
                )
            elif format_type == "GLTF":
                bpy.ops.export_scene.gltf(
                    filepath = file_path + ".gltf",
                    use_selection = True,
                    export_format = "GLTF_SEPARATE"
                )
            elif format_type == "STL":
                bpy.ops.export_mesh.stl(
                    filepath = file_path + ".stl",
                    use_selection = True,
                    global_scale = scene.mesh_export_scale
                )

            # Restore original location if needed
            if scene.mesh_export_zero_location:
                obj.location = original_location
        

        # Restore original state
        # for obj in mesh_objects:
        #     if obj.name in original_scale:
        #         obj.scale = original_scale[obj.name]
        
        # Restore original position and rotation if needed
        # if scene.mesh_export_zero_rotation:
            # for obj in mesh_objects:
            #     obj.rotation_euler = (0, 0, 0)
        # if scene.mesh_export_zero_location:
            # for obj in mesh_objects:
            #     obj.location = (0, 0, 0)
        
        # Restore selection
        for obj in selected_objects:
            obj.select_set(True)
        
        self.report({"INFO"}, f"Successfully exported {len(mesh_objects)} objects to {export_path}")
        return {"FINISHED"}

classes = (
    MESH_OT_batch_export,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)