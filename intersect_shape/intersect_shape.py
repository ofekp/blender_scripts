
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


def strVector3( v3 ):
    return str(v3.x) + "," + str(v3.y) + "," + str(v3.z)


def save_obj_file(main_intersect_dataset_folder, is_intersecting_faces, idx):
    blend_file_path = main_intersect_dataset_folder + "\\" + str(is_intersecting_faces) + "\\"
    file_path = os.path.dirname(blend_file_path)
    target_file = os.path.join(file_path, "{:03d}.obj".format(idx))
    bpy.ops.export_scene.obj(filepath=target_file)
    os.remove(os.path.join(file_path, "{:03d}.mtl".format(idx)))


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


num_of_iterations = 50
main_intersect_dataset_folder = "D:\\TAU MSc\\Semester 4\\Thesis\\Intersections\\SubdivNet\\data\\Intersect"
dirs = [main_intersect_dataset_folder + "\\false", main_intersect_dataset_folder + "\\true"]

for dir in dirs:
    if not os.path.exists(dir):
        os.makedirs(dir)

intersect_idx = 0
no_intersect_idx = 0
for i in range(num_of_iterations):
    # create an ico sphere
    bpy.ops.mesh.primitive_ico_sphere_add()

    # newly created ico sphere will be automatically selected
    ico = bpy.context.selected_objects[0]
    ico.name = "ico"

    # change its location
    ico.location = (0.0, 0.0, 0.0)

    mat_world = ico.matrix_world
    for v in bpy.context.active_object.data.vertices:
        if random.random() > 0.5:
            v.co[0] += random.random() * 0.6
            v.co[1] += random.random() * 0.6
            v.co[2] += random.random() * 0.6
    is_intersecting = len(detect_intersection(bpy.context.active_object)) > 0
    if is_intersecting:
        idx = intersect_idx
        intersect_idx += 1
    else:
        idx = no_intersect_idx
        no_intersect_idx += 1
    save_obj_file(main_intersect_dataset_folder, is_intersecting, idx)
    bpy.ops.object.delete()
