import bpy
import bpy_extras
import math
import random
from mathutils import Vector
import json
import os


def rand_minus_one_to_one():
    return 2.0 * (random.random() - 0.5)


# currently not used
def add_track_to_constraint():
    # Add a new track to constraint and set it to track your object
    track_to = bpy.context.object.constraints.new('TRACK_TO')
    track_to.target = target_object
    track_to.track_axis = 'TRACK_NEGATIVE_Z'
    track_to.up_axis = 'UP_Y'
    
    
def look_at(obj_camera, point):
    loc_camera = obj_camera.matrix_world.to_translation()
    direction = point - loc_camera
    # point the cameras '-Z' and use its 'Y' as up
    rot_quat = direction.to_track_quat('-Z', 'Y')
    # assume we're using euler rotation
    obj_camera.rotation_euler = rot_quat.to_euler()
    
    
def convert_matrix_to_array(mat):
    arr = []
    for l in mat:
        arr.append([elem for elem in l])
    return arr
    

def main():
    # first, set in Output Properties the resolution to 800x800 pixels (though can use less)
    # Render Properties -> Film -> Transparent
    skip_cameras_placement = False
    skip_render = False
    is_sphere = True
    assert not skip_cameras_placement or not skip_render

    bb_size = 0.1
#    z_min = 1
#    z_max = 2.5
    radius_factor = 0.05
    splits = [('train', 30), ('val', 30), ('test', 30)]
    main_dir = "D:\\TAU MSc\\Semester 4\\Thesis\\NeRF\\Blender\\renders\\sphere_128"
    if is_sphere:
        theta = math.pi
        phi = math.pi / 2
    else:
        theta = math.pi / 4.0
        phi_min = math.pi / 12.0
        phi_max = math.pi / 10.0
    #splits = [('train', 2)]

    if not skip_cameras_placement:
        # delete all cameras
        scn = bpy.context.scene
        for obj in scn.objects:
            if obj.name.startswith("camera_"):
                # Deselect all
                bpy.ops.object.select_all(action='DESELECT')
                # Select the object
                obj.select_set(True)
                bpy.ops.object.delete()
        
        frames = []
#        z_adjust = ((z_max - z_min) / 2)
        for dataset_name, img_count in splits:
            for c in range(img_count):
                camera = bpy.data.objects['MainCamera']  # Make sure your first camera is named 'MainCamera'
                target_object = bpy.data.objects['Suzanne']  # The camera will face this object

                z = camera.location[2]
                radius = Vector((camera.location[0], camera.location[1], 0)).length
                angle = theta * rand_minus_one_to_one() - (math.pi / 2)

                # Randomly place the camera on a circle around the object at the same height as the main camera
                radius_rand = radius + (radius_factor * rand_minus_one_to_one())
#                rand_z = (z_adjust * rand_minus_one_to_one()) + (z_adjust + z_min)
                if is_sphere:
                    r = random.random()
                    phi_rand = phi * r * r
                else:
                    phi_rand = ((phi_min + phi_max) / 2) + rand_minus_one_to_one() * ((phi_max - phi_min) / 2)
                new_camera_pos = Vector((radius_rand * math.cos(angle) * math.cos(phi_rand), radius_rand * math.sin(angle) * math.cos(phi_rand), radius_rand * math.sin(phi_rand)))

                bpy.ops.object.camera_add(enter_editmode=False, location=new_camera_pos)
                new_camera = bpy.context.active_object
                new_camera.name = "camera_" + dataset_name + '_' + str(c).zfill(3)
                new_camera.data.name = "camera_" + dataset_name + '_' + str(c).zfill(3)

                look_at_point = Vector((bb_size * rand_minus_one_to_one(), bb_size * rand_minus_one_to_one(), bb_size * rand_minus_one_to_one()))
                look_at(new_camera, look_at_point)

                # Set the new camera as active
                bpy.context.scene.camera = bpy.context.object


    if not skip_render:
        scn = bpy.context.scene
        for dataset_name, img_count in splits:
            os.mkdir(os.path.join(main_dir, dataset_name))
            meta = {}
            frames = []
            for obj in scn.objects:
                if obj.name.startswith("camera_" + dataset_name):
                    img_idx_str = obj.name.split('_')[2]  # get the camera number e.g. 005
                    print("Rendering for camera [{}]".format(obj.name))
                    scn.camera = obj
                    scn.render.filepath = os.path.join(main_dir, dataset_name, "r_" + img_idx_str)
                    bpy.ops.render.render(write_still=True)
                    print("Done rendering for camera [{}]".format(obj.name))
                    if "camera_angle_x" not in meta:
                        meta["camera_angle_x"] = obj.data.angle
                    frames.append({
                        'file_path': os.path.join('./', dataset_name, "r_" + img_idx_str).replace("\\","/"),
                        'transform_matrix': convert_matrix_to_array(obj.matrix_world),
                    })
            meta["frames"] = frames
            with open(os.path.join(main_dir, "transforms_" + dataset_name + ".json"), 'w') as transforms_file:
                transforms_file.write(json.dumps(meta, indent=4))


if __name__ == "__main__":
    main()