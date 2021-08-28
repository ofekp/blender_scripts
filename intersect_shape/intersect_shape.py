
#import bpy

#vertices = [(0, 0, 0),]
#edges = []
#faces = []

#new_mesh = bpy.data.meshes.new('new_mesh')
#new_mesh.from_pydata(vertices, edges, faces)
#new_mesh.update()

#new_object = bpy.data.objects.new('new_object', new_mesh)
#Python
#new_collection = bpy.data.collections.new('new_collection')
#bpy.context.scene.collection.children.link(new_collection)
#    
#new_collection.objects.link(new_object)


import bpy
import random
import mathutils
from object_print3d_utils import mesh_helpers
import array
import os
import math
from pathlib import Path
import time
import bmesh


def strVector3( v3 ):
    return str(v3.x) + "," + str(v3.y) + "," + str(v3.z)


def save_obj_file(main_intersect_dataset_folder, is_intersecting_faces, is_train, idx):
    blend_file_path = main_intersect_dataset_folder + "\\" + str(is_intersecting_faces) + "\\" + ("train" if is_train else "test") + "\\"
    file_path = os.path.dirname(blend_file_path)
    target_file = os.path.join(file_path, "{:03d}.obj".format(idx))
    bpy.ops.export_scene.obj(filepath=target_file, use_materials=False)
    

def load_obj_file(filepath):
    bpy.ops.import_scene.obj(filepath=filepath)
    return bpy.context.selected_objects[0]


def detect_intersection(obj):
    """
    found on:
    https://blenderartists.org/t/self-intersection-detection/671080
    documentation of the intersection detection method
    https://docs.blender.org/api/current/mathutils.bvhtree.html
    """
    if not obj.data.polygons:
        return array.array('i', ())

    bm = mesh_helpers.bmesh_copy_from_object(obj, transform=False, triangulate=False)
    
    tree = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.00001)

    overlap = tree.overlap(tree)
    faces_error = {i for i_pair in overlap for i in i_pair}
    return array.array('i', faces_error)


def generate_dataset(main_intersect_dataset_folder, examples_per_label=800, train_test_ratio=0.8):
    # intersect_train, intersect_test, non_intersect_train, non_intersect_test
    required_counts = [train_test_ratio * examples_per_label, (1 - train_test_ratio) * examples_per_label] * 2
    required_counts = [math.ceil(c) for c in required_counts]
    counts = [0, 0, 0, 0]
    
    # check if some files already exist
    dirs = [main_intersect_dataset_folder + "\\false",
        main_intersect_dataset_folder + "\\true",
        main_intersect_dataset_folder + "\\false\\train",
        main_intersect_dataset_folder + "\\false\\test",
        main_intersect_dataset_folder + "\\true\\train",
        main_intersect_dataset_folder + "\\true\\test"]
   
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
        else:
            idx = 0 if "true" in dir else 2
            idx += 0 if "train" in dir else 1
            counts[idx] = len(Path(dir).rglob('*.obj'))
    
    total_time = 0
    num_executions = 0
    while sum(counts) < sum(required_counts):
        # create an ico sphere
        bpy.ops.mesh.primitive_ico_sphere_add()

        # newly created ico sphere will be automatically selected
        ico = bpy.context.selected_objects[0]
        ico.name = "ico"
#        ico.scale = (0.3, 0.3, 0.3)
        bpy.ops.transform.resize(value=(0.2, 0.2, 0.2))

        # change its location
        ico.location = (0.0, 0.0, 0.0)
        # change to shade smooth to avoide saving the object with any sharp edges
        for f in bpy.context.active_object.data.polygons:
            f.use_smooth = True

        mat_world = ico.matrix_world
        for v in bpy.context.active_object.data.vertices:
            if random.random() > 0.5:
                v.co[0] += random.random() * 0.5
                v.co[1] += random.random() * 0.5
                v.co[2] += random.random() * 0.5
        ts = time.time()
        is_intersecting = len(detect_intersection(bpy.context.active_object)) > 0
        num_executions += 1
        total_time += time.time() - ts
        idx = 0 if is_intersecting else 2
        is_train = counts[idx] < required_counts[idx]
        idx += 0 if is_train else 1
        if not is_train and counts[idx] >= required_counts[idx]:
            bpy.ops.object.delete()
            continue
        save_obj_file(main_intersect_dataset_folder, is_intersecting, is_train, counts[idx])
        counts[idx] += 1
        bpy.ops.object.delete()
      
    print(required_counts)  
    print(counts)
    print("Intersect avg run time [{}]".format(str(total_time / num_executions)))
    
    
def check_dataset(main_intersect_dataset_folder, remove_bad_files=False, rename_files=False, is_assert=False):
    pathlist = Path(main_intersect_dataset_folder).rglob('*.obj')
    count_bad = 0
    count_all = 0
    files_to_remove = []
    for path in pathlist:
        path_str = str(path)
        ico = load_obj_file(path_str)
        if "true" in path_str:
            if is_assert:
                assert len(detect_intersection(ico)) > 0
            if len(detect_intersection(ico)) == 0:
                count_bad += 1
                files_to_remove.append(path_str)
        elif "false" in path_str:
            if is_assert:
                assert len(detect_intersection(ico)) == 0
            if len(detect_intersection(ico)) > 0:
                count_bad += 1
                files_to_remove.append(path_str)
        count_all += 1
        bpy.ops.object.delete()
    print("Found [{}/{}] bad data examples".format(count_bad, count_all))
    if remove_bad_files:
        for file in files_to_remove:
            print("Removing file [{}]".format(file))
            os.remove(file)
    # rename files
    if rename_files:
        dirs = [main_intersect_dataset_folder + "\\false\\train",
                main_intersect_dataset_folder + "\\false\\test",
                main_intersect_dataset_folder + "\\true\\train",
                main_intersect_dataset_folder + "\\true\\test"]
        for dir in dirs:
            i = 0
            pathlist = Path(dir).rglob('*.obj')
            for path in pathlist:
                path_str = str(path)
                path_obj = os.path.abspath(path_str)
                new_path_str = str(os.path.join(os.path.dirname(path_obj), "{:03d}.obj".format(i)))
                print("Renaming file [{}]\n" \
                      "to            [{}]".format(path_str, new_path_str))
                os.rename(path_str, new_path_str)
                i += 1

         
def select_intersecting_faces():
    # must be in edit mode and then deselect all to use this method
    obj = bpy.context.edit_object
    face_indices = detect_intersection(obj)
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    # notice in Bmesh polygons are called faces
    for face_index in face_indices:
        bm.faces[face_index].select = True
    # Show the updates in the viewport
    bmesh.update_edit_mesh(me, True)
    

if __name__ == "__main__":
#    generate_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapes")
#    check_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapes", remove_bad_files=False, is_assert=True)
#    check_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapes-MAPS-96-3", remove_bad_files=True, rename_files=False, is_assert=False)
    select_intersecting_faces()