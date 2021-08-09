
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

def strVector3( v3 ):
    return str(v3.x) + "," + str(v3.y) + "," + str(v3.z)

def detect_intersection(obj):
    """
    found on:
    https://blenderartists.org/t/self-intersection-detection/671080
    """
    if not obj.data.polygons:
        return array.array('i', ())

    bm = mesh_helpers.bmesh_copy_from_object(obj, transform=False, triangulate=False)
    
    tree = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.00001)

    overlap = tree.overlap(tree)
    faces_error = {i for i_pair in overlap for i in i_pair}
    return array.array('i', faces_error)

# create a new cube
bpy.ops.mesh.primitive_ico_sphere_add()

# newly created cube will be automatically selected
ico = bpy.context.selected_objects[0]
# change name
ico.name = "ico"

# change its location
ico.location = (0.0, 0.0, 0.0)

index_list = []
tracker_list = []
mat_world = ico.matrix_world
for v in bpy.context.active_object.data.vertices:
#    pos_world = mat_world * v.co
#    pos_world.z += 0.3
#    v.co = mat_world.inverted() * pos_world
    if random.random() > 0.5:
        v.co[0] += random.random() * 0.7
        v.co[1] += random.random() * 0.7
        v.co[2] += random.random() * 0.7
    print(detect_intersection(bpy.context.active_object))


#bpy.ops.object.editmode_toggle()

#bpy.ops.transform.translate(value=(-0.0635778, 0.323402, -0.197673), orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), 
#                            orient_matrix_type='GLOBAL', mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, 
#                            use_proportional_connected=False, use_proportional_projected=False)

#bpy.ops.object.editmode_toggle()
