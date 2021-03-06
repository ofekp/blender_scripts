
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
import json
import re
import sys
import shutil


def install_requirements():
    # this might require running Blender as administrator
    # this did not really work (tried on Win10), I had to give write permissions to all users to python folder in
    #   C:\Program Files\Blender Foundation\Blender 2.91\2.91\python
    # then in windows' CMD:
    #   cd "C:\Program Files\Blender Foundation\Blender 2.91\2.91\python\bin"
    #   "C:\Program Files\Blender Foundation\Blender 2.91\2.91\python\bin\python" -m pip install tqdm
    import subprocess
    import ensurepip
    print("---")
    ensurepip.bootstrap()
    pybin = sys.executable  # bpy.app.binary_path_python
#    subprocess.check_call([pybin, '-m', 'pip', 'cache', 'purge'])
#    subprocess.check_call([pybin, '-m', 'pip', 'install', '--upgrade', 'pip'])
    subprocess.check_call([pybin, '-m', 'pip', '--version'])
    subprocess.check_call([pybin, '-m', 'pip', 'install', 'tqdm'])

#install_requirements()
from tqdm import tqdm


def strVector3( v3 ):
    return str(v3.x) + "," + str(v3.y) + "," + str(v3.z)


def save_obj_file(main_intersect_dataset_folder, is_intersecting_faces, is_train, idx):
    blend_file_path = main_intersect_dataset_folder + "\\" + str(is_intersecting_faces) + "\\" + ("train" if is_train else "test") + "\\"
    file_path = os.path.dirname(blend_file_path)
    target_file = os.path.join(file_path, "{:04d}.obj".format(idx))
    bpy.ops.export_scene.obj(filepath=target_file, use_materials=False, keep_vertex_order=True)
    

def load_obj_file(filepath):
    bpy.ops.import_scene.obj(filepath=filepath, split_mode='OFF')
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
    

def generate_intersecting_faces_list(obj):
    face_indices = detect_intersection(obj)
    me = obj.data
    num_of_faces = len(me.polygons)
    res = [1] * num_of_faces  # non intersecting
    for face_index in face_indices:
        res[face_index] = 2  # intersecting
    return res


def generate_face_mapping(from_obj, to_obj):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = from_obj
    bpy.ops.object.editmode_toggle()
    from_obj_data = from_obj.data
    from_bm = bmesh.from_edit_mesh(from_obj_data)
    from_bm_face_centers = []
    for face in from_bm.faces:
        c = face.calc_center_median()
        from_bm_face_centers.append(c)
    
    bpy.ops.object.editmode_toggle()
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = to_obj
    bpy.ops.object.editmode_toggle()
    to_obj_data = to_obj.data
    to_bm = bmesh.from_edit_mesh(to_obj_data)
    bvhtree = mathutils.bvhtree.BVHTree.FromBMesh(to_bm, epsilon=0.00001)
    
    mapping = []
    for face_center in from_bm_face_centers:
        pos, norm, idx, d = bvhtree.find_nearest(face_center)
        if pos is not None: # is zero vector boolean False?
            for to_face_idx, f in enumerate(to_bm.faces):
                if f.index == idx:
                    mapping.append(to_face_idx)
                    break
                to_face_idx += 1

    bpy.ops.object.editmode_toggle()
    return mapping


def generate_face_mapping_visualize_single_face_in_edit_mode(from_obj, to_obj):
    """
    for DEBUG only
    """
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = from_obj
    bpy.ops.object.editmode_toggle()
    from_obj_data = from_obj.data
    from_bm = bmesh.from_edit_mesh(from_obj_data)
    for face in from_bm.faces:
        face.select = False
    for face in from_bm.faces:
        face.select = True
        c = face.calc_center_median()
        bmesh.update_edit_mesh(from_obj_data, True)
        time.sleep(5)
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = to_obj
        bpy.ops.object.editmode_toggle()
        to_obj_data = to_obj.data
        to_bm = bmesh.from_edit_mesh(to_obj_data)
        bvhtree = mathutils.bvhtree.BVHTree.FromBMesh(to_bm, epsilon=0.00001)
        pos, norm, idx, d = bvhtree.find_nearest(c)
        if pos is not None: # is zero vector boolean False?
            for f in to_bm.faces:
                f.select = f.index == idx
            bmesh.update_edit_mesh(to_obj_data, True)
        break
    return ""


def generate_segmentation_dataset_json_files(original_folder, maps_folder):
    pathlist = Path(maps_folder).rglob('*.obj')
    for path in tqdm(pathlist):
        maps_path_str = str(path)
#        orig_path_str = maps_path_str.replace(maps_folder, original_folder).replace("-0.obj", ".obj")
        orig_path_str = maps_path_str  # use this when the original object should be identical to the remeshed object
        bpy.ops.import_scene.obj(filepath=maps_path_str)
        maps_obj = bpy.context.selected_objects[0]
        bpy.ops.import_scene.obj(filepath=orig_path_str)
        orig_obj = bpy.context.selected_objects[0]
        data = {
            "raw_labels": generate_intersecting_faces_list(orig_obj),
            "raw_to_sub": generate_face_mapping(orig_obj, maps_obj),
            "sub_labels": generate_intersecting_faces_list(maps_obj),
        }
        with open(maps_path_str.replace(".obj", ".json"), 'w') as json_file:
            json.dump(data, json_file)
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        
        
def arragne_folder_structure_for_segmentation(original_folder, maps_folder, target_folder, dataset_name):
    # check if some files already exist
    dirs = [target_folder,
            target_folder + "\\train",
            target_folder + "\\train\\" + dataset_name,
            target_folder + "\\test",
            target_folder + "\\test\\" + dataset_name,
            target_folder + "\\raw"]
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)
    
    pathlist = Path(maps_folder).rglob(r'*.obj')
    for path in tqdm(pathlist):
        path_str = str(path)
        is_train = "train" in path_str
        is_intersecting = "true" in path_str
        file_name = "{}_{}_{:04d}-0.obj".format(("train" if is_train else "test"), ("intersecting" if is_intersecting else "not_intersecting"), int(path.name.split('-')[0]))
        target_path = target_folder + "\\" + ("train" if is_train else "test") + "\\" + dataset_name + "\\" + file_name
#        original_file = original_folder + "\\" + str(is_intersecting).lower() + "\\" + ("train" if is_train else "test") + "\\" + path.name.split('-')[0] + ".obj"
        original_file = maps_folder + "\\" + str(is_intersecting).lower() + "\\" + ("train" if is_train else "test") + "\\" + path.name.split('-')[0] + "-0.obj"
        raw_file = target_folder + "\\raw\\" + ("train" if is_train else "test") + "_" + ("intersecting" if is_intersecting else "not_intersecting") + "_" + "{:04d}".format(int(path.name.split('-')[0])) + ".obj"
#        print("[{}] --> [{}]".format(original_file, raw_file))
#        print("[{}] --> [{}]".format(path_str, target_path))
#        print("[{}] --> [{}]".format(path_str.replace("obj", "json"), target_path.replace("obj", "json")))
#        break
        shutil.copy(original_file, raw_file)
        shutil.copy(path_str, target_path)
        shutil.copy(path_str.replace("obj", "json"), target_path.replace("obj", "json"))
    

def add_empty(location):
    bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    bpy.ops.transform.resize(value=(0.01, 0.01, 0.01), orient_type='LOCAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)
    bpy.ops.transform.translate(value=tuple(location), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)


def convert_to_ply(raw_obj_folder):
    pathlist = Path(raw_obj_folder).rglob(r'*.obj')
    for path in tqdm(pathlist):
        path_str = str(path)
        obj = load_obj_file(path_str)
        # save as ply to the same folder
        bpy.ops.export_mesh.ply(filepath=path_str.replace(".obj", ".ply"))
        shutil.move(path_str, path_str.replace("\\raw", "\\raw\\objs"))
        bpy.ops.object.delete()


def visualize_trimesh_load():
    """
    for DEBUG only
    """
    import trimesh
    from mathutils import Vector
    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentationFinal-MAPS-96-3\\train\\icosphere\\train_intersecting_0011-0.obj"
    obj = load_obj_file(obj_path)
    intersecting_faces = detect_intersection(obj)
    
#    bpy.ops.object.select_all(action='DESELECT')
#    bpy.context.view_layer.objects.active = obj
#    bpy.ops.object.editmode_toggle()
#    obj_data = obj.data
#    obj_bm = bmesh.from_edit_mesh(obj_data)
#    face_centers = []
#    for face in obj_bm.faces:
#        face.select = False
#    for idx, face in enumerate(obj_bm.faces):
#        if idx in intersecting_faces:
#            face.select = True
#            face_center = face.calc_center_median()
#            print(face_center)
#            face_centers.append(face_center)
#    bpy.ops.object.editmode_toggle()
#    for face_center in face_centers:
#        add_empty(obj.matrix_world @ Vector(face_center))

    
#    for idx, face in enumerate(obj.data.polygons):
#        if idx in intersecting_faces:
#            face_center = face.center
#            add_empty(obj.matrix_world @ Vector(face_center))


#    mesh = trimesh.load_mesh(obj_path, process=False)
##    mesh = trimesh.load(obj_path, process=False, maintain_order=True)
#    for idx, face in enumerate(mesh.faces):
#        if idx in intersecting_faces:
#            face_center = mesh.vertices[face].mean(axis=0)
#            print("tirmesh [{}] obj [{}]".format(face_center, obj.data.polygons[idx].center))
#            print("world trimesh [{}] world obj [{}]".format(obj.matrix_world @ Vector(face_center), obj.matrix_world @ obj.data.polygons[idx].center))
#            add_empty(obj.matrix_world @ Vector(face_center))


if __name__ == "__main__":
    # classification dataset
#    generate_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrdered")
#    check_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrdered", remove_bad_files=False, is_assert=True)
    # go to anaconda
    #   D:
    #   cd "D:\TAU MSc\Semester 4\Thesis\Intersections\SubdivNet"
    #   conda activate subdivnet
    #   in subdivnet code modify the script "datagen_maps.py" according to the dataset
    #   python datagen_maps.py
#    check_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrdered-MAPS-96-3", remove_bad_files=False, rename_files=False, is_assert=True)
    # if there are any reasonable number of bad shapes, remove them with the following line
#    check_dataset("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrdered-MAPS-96-3", remove_bad_files=True, rename_files=False, is_assert=False)

    # segmentation dataset
    # generate a classification dataset using the steps above
    # copy that datset to another folder for segmentation
#    generate_segmentation_dataset_json_files("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentation-MAPS-96-3",
#                                             "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentation-MAPS-96-3")
#    arragne_folder_structure_for_segmentation("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesSeg",  # not used
#                                              "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentation-MAPS-96-3",
#                                              "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentationFinal-MAPS-96-3",
#                                              "icosphere")


#    convert_to_ply("D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentationFinal-MAPS-96-3\\raw\\")


    # based on https://blender.stackexchange.com/questions/30314/file-format-with-per-face-colors
    import trimesh
#    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\results\\HumanBody\\gt-11.ply"
#    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\results\\IntersectShapesOrderedSegmentationFinal\\pred-test_intersecting_01.ply"
#    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\results\\IntersectShapesOrderedSegmentationFinal\\pred-test_intersecting_00.ply"
    bpy.ops.import_mesh.ply(filepath=obj_path)
    obj = bpy.context.selected_objects[0]
    if not obj.data.vertex_colors:
        # creates one 'Col' by default
        obj.data.vertex_colors.new()
    color_layer = obj.data.vertex_colors['Col']
    
    mesh = trimesh.load_mesh(obj_path, process=False)
    i = 0
    for idx, color in enumerate(mesh.visual.face_colors):
        verts = mesh.faces[idx]
        for vert in verts:
            color_layer.data[i].color = color[:4] / 255
            i += 1
    
    # DEBUG
#    select_intersecting_faces()  # must be in edit mode
#    print(generate_raw_labels())

#    import trimesh
##    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\results\\HumanBody\\gt-6.ply"
##    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\intersect_shape_tmp.ply"
#    obj_path = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\IntersectShapesOrderedSegmentationFinal-MAPS-96-3\\raw\\test_intersecting_0000.ply"
#    mesh = trimesh.load_mesh(obj_path, process=False)
#    print(mesh.visual.face_colors[:5, :3])
