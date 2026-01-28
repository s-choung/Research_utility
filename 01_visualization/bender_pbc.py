import bpy
import mathutils
from pathlib import Path
from math import pi, sqrt


def make_all_materials_metallic():
    """Set materials to slightly metallic appearance, except H"""
    for mat in bpy.data.materials:
        if mat.node_tree and "Principled BSDF" in mat.node_tree.nodes:
            bsdf = mat.node_tree.nodes["Principled BSDF"]
            
            # Skip hydrogen - keep it non-metallic
            if mat.name.lower() in ['hydrogen', 'h']:
                bsdf.inputs["Metallic"].default_value = 0.0
                bsdf.inputs["Roughness"].default_value = 0.5
                print(f"  '{mat.name}' kept non-metallic")
            else:
                # Subtle metallic look (0.4 instead of 1.0)
                bsdf.inputs["Metallic"].default_value = 0.4
                bsdf.inputs["Roughness"].default_value = 0.4
                print(f"  Made '{mat.name}' slightly metallic")

def print_all_objects():
    """Print all objects in the scene for debugging"""
    print("\n--- All objects in scene ---")
    for obj in bpy.data.objects:
        print(f"  Name: '{obj.name}', Type: {obj.type}, Location: {obj.location[:]}")
    print("----------------------------\n")


def parse_lattice_from_poscar(filepath):
    """Parse lattice vectors from VASP POSCAR file"""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 5:
        return None
    
    # Line 1: comment
    # Line 2: scaling factor
    try:
        scale = float(lines[1].strip())
    except ValueError:
        scale = 1.0
    
    # Lines 3-5: lattice vectors
    try:
        a_vals = [float(x) * scale for x in lines[2].split()]
        b_vals = [float(x) * scale for x in lines[3].split()]
        c_vals = [float(x) * scale for x in lines[4].split()]
        
        a = mathutils.Vector((a_vals[0], a_vals[1], a_vals[2]))
        b = mathutils.Vector((b_vals[0], b_vals[1], b_vals[2]))
        c = mathutils.Vector((c_vals[0], c_vals[1], c_vals[2]))
        
        return a, b, c
    except (ValueError, IndexError) as e:
        print(f"  Error parsing POSCAR: {e}")
        return None


def create_pbc_lines(lattice_vectors, origin=None, line_radius=0.03, line_color=(0.2, 0.2, 0.2, 1.0)):
    """Create unit cell boundary lines from lattice vectors"""
    if lattice_vectors is None:
        print("  No lattice vectors found, skipping PBC lines")
        return
    
    a, b, c = lattice_vectors
    
    if origin is None:
        origin = mathutils.Vector((0, 0, 0))
    else:
        origin = mathutils.Vector(origin)
    
    # 8 corners of the unit cell
    corners = [
        origin,                    # 0: origin
        origin + a,                # 1: +a
        origin + b,                # 2: +b
        origin + c,                # 3: +c
        origin + a + b,            # 4: +a+b
        origin + a + c,            # 5: +a+c
        origin + b + c,            # 6: +b+c
        origin + a + b + c,        # 7: +a+b+c
    ]
    
    # 12 edges of the unit cell (pairs of corner indices)
    edges = [
        (0, 1), (0, 2), (0, 3),    # From origin
        (1, 4), (1, 5),            # From +a
        (2, 4), (2, 6),            # From +b
        (3, 5), (3, 6),            # From +c
        (4, 7), (5, 7), (6, 7),    # To +a+b+c
    ]
    
    # Create material for PBC lines
    mat_name = "PBC_Line_Material"
    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
    else:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = line_color
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.8
    
    # Create cylinder for each edge
    for i, (start_idx, end_idx) in enumerate(edges):
        start = corners[start_idx]
        end = corners[end_idx]
        
        # Calculate cylinder parameters
        direction = end - start
        length = direction.length
        center = (start + end) / 2
        
        # Create cylinder
        bpy.ops.mesh.primitive_cylinder_add(
            radius=line_radius,
            depth=length,
            location=center
        )
        
        cylinder = bpy.context.active_object
        cylinder.name = f"PBC_Edge_{i}"
        
        # Rotate cylinder to align with edge direction
        up = mathutils.Vector((0, 0, 1))
        if direction.normalized().cross(up).length > 0.001:
            rot_quat = up.rotation_difference(direction.normalized())
            cylinder.rotation_mode = 'QUATERNION'
            cylinder.rotation_quaternion = rot_quat
        
        # Apply material
        cylinder.data.materials.append(mat)
    
    print(f"  Created 12 PBC unit cell edges")
    print(f"  Lattice vectors: a={a.length:.2f}, b={b.length:.2f}, c={c.length:.2f} A")


def clear_all_mesh_and_empty_objects():
    """Remove all mesh objects AND empty objects from scene (keep Camera and Light)"""
    bpy.ops.object.select_all(action='DESELECT')
    
    objects_to_delete = []
    for obj in bpy.data.objects:
        if obj.type not in ['CAMERA', 'LIGHT']:
            objects_to_delete.append(obj.name)
            obj.select_set(True)
    
    if objects_to_delete:
        print(f"Deleting objects: {objects_to_delete}")
        bpy.ops.object.delete()
    
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)


def get_scene_bounds():
    """Calculate bounding box center and size of all mesh objects (excluding PBC lines)"""
    min_coords = [float('inf')] * 3
    max_coords = [float('-inf')] * 3
    
    for obj in bpy.data.objects:
        # Skip PBC edge objects
        if obj.type == 'MESH' and not obj.name.startswith('PBC_'):
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    min_coords[i] = min(min_coords[i], world_corner[i])
                    max_coords[i] = max(max_coords[i], world_corner[i])
    
    center = [(min_coords[i] + max_coords[i]) / 2 for i in range(3)]
    size = [max_coords[i] - min_coords[i] for i in range(3)]
    max_dimension = max(size)
    
    return center, size, max_dimension


def setup_render_settings():
    """Apply render settings with transparent background"""
    bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.eevee.taa_render_samples = 32
    
    # Transparent background
    bpy.context.scene.render.film_transparent = True
    
    # PNG for transparency
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.image_settings.color_mode = 'RGBA'
    bpy.context.scene.render.image_settings.compression = 15
    
    # Resolution
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080


def setup_lights(center, max_dim):
    """Setup multi-angle lighting for better illumination"""
    
    # Remove existing lights first
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Distance for lights based on structure size
    light_dist = max_dim * 2.0
    
    # Light configurations: (name, type, energy, position_offset, color)
    # Position offsets are relative to structure center
    lights_config = [
        # Key light - main light from upper front-left
        {
            'name': 'Key_Light',
            'type': 'SUN',
            'energy': 2.0,
            'location': (center[0] - light_dist, center[1] - light_dist, center[2] + light_dist * 1.5),
            'rotation': (45 * pi / 180, -30 * pi / 180, 0),
            'color': (1.0, 1.0, 1.0),
        },
        # Fill light - softer light from right side
        {
            'name': 'Fill_Light',
            'type': 'SUN',
            'energy': 1.0,
            'location': (center[0] + light_dist, center[1] - light_dist * 0.5, center[2] + light_dist * 0.5),
            'rotation': (60 * pi / 180, 30 * pi / 180, 0),
            'color': (0.95, 0.95, 1.0),
        },
        # Back light - rim lighting from behind
        {
            'name': 'Back_Light',
            'type': 'SUN',
            'energy': 1.2,
            'location': (center[0], center[1] + light_dist, center[2] + light_dist),
            'rotation': (-45 * pi / 180, 0, 0),
            'color': (1.0, 1.0, 0.95),
        },
        # Top light - illumination from above
        {
            'name': 'Top_Light',
            'type': 'SUN',
            'energy': 0.6,
            'location': (center[0], center[1], center[2] + light_dist * 2),
            'rotation': (0, 0, 0),
            'color': (1.0, 1.0, 1.0),
        },
        # Bottom fill - subtle light from below to reduce harsh shadows
        {
            'name': 'Bottom_Fill',
            'type': 'SUN',
            'energy': 0.3,
            'location': (center[0], center[1], center[2] - light_dist),
            'rotation': (180 * pi / 180, 0, 0),
            'color': (0.9, 0.9, 1.0),
        },
    ]
    
    for config in lights_config:
        # Create light data
        light_data = bpy.data.lights.new(name=config['name'], type=config['type'])
        light_data.energy = config['energy']
        light_data.color = config['color']
        
        # Create light object
        light_obj = bpy.data.objects.new(name=config['name'], object_data=light_data)
        bpy.context.collection.objects.link(light_obj)
        
        # Set position and rotation
        light_obj.location = config['location']
        light_obj.rotation_mode = 'XYZ'
        light_obj.rotation_euler = config['rotation']
        
        print(f"  Added {config['name']}: energy={config['energy']}, at {config['location']}")


def setup_camera_perspective(center, max_dim):
    """Set camera to angled orthographic view, auto-positioned based on structure size"""
    camera = bpy.data.objects['Camera']
    
    # Orthographic projection (no lens distortion)
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max_dim * 2.0  # Visible area
    
    # Fix clipping distance
    camera.data.clip_start = 0.1
    camera.data.clip_end = 10000
    
    distance_factor = 3.0
    distance = max_dim * distance_factor
    
    camera.location = (
        center[0],
        center[1] - distance * 0.9,
        center[2] + distance * 0.5
    )
    camera.rotation_mode = 'XYZ'
    camera.rotation_euler = (65 * (pi / 180.0), 0, 0)
    
    print(f"  Ortho camera (angled):")
    print(f"    ortho_scale={camera.data.ortho_scale:.1f}")
    print(f"    location={camera.location[:]}")
    print(f"    clip_start={camera.data.clip_start}, clip_end={camera.data.clip_end}")


def setup_camera_top(center, max_dim):
    """Set camera to top orthographic view, auto-positioned based on structure size"""
    camera = bpy.data.objects['Camera']
    
    # Orthographic projection
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = max_dim * 1.8  # Adjust framing
    
    # Fix clipping distance
    camera.data.clip_start = 0.1
    camera.data.clip_end = 10000
    
    distance_factor = 4.0
    distance = max_dim * distance_factor
    
    camera.location = (center[0], center[1], center[2] + distance)
    camera.rotation_mode = 'XYZ'
    camera.rotation_euler = (0, 0, 0)
    
    print(f"  Ortho camera (top):")
    print(f"    ortho_scale={camera.data.ortho_scale:.1f}")
    print(f"    location={camera.location[:]}")


def main():
    # TEST MODE - single file
    test_file = Path('/Users/sean/Library/CloudStorage/OneDrive-postech.ac.kr/연구/playground/2_LLM_Catal_agent/PtSn_alloys/output/L12_Pt3Sn/L12_Pt3Sn_H_top1_relaxed_2x2.xyz')
    
    # POSCAR directory
    poscar_dir = Path('/Users/sean/Library/CloudStorage/OneDrive-postech.ac.kr/연구/playground/2_LLM_Catal_agent/PtSn_alloys/test_run_L10_SnPt')
    
    # Output directory
    output_dir = Path('/Users/sean/Library/CloudStorage/OneDrive-postech.ac.kr/연구/playground/2_LLM_Catal_agent/PtSn_alloys/rendered_images_test')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find POSCAR file
    poscar_files = list(poscar_dir.glob('*.vasp')) + list(poscar_dir.glob('POSCAR*'))
    poscar_file = poscar_files[0] if poscar_files else None
    if poscar_file:
        print(f"Using POSCAR: {poscar_file.name}")
    else:
        print("No POSCAR file found!")
    
    # Clear objects
    print("Clearing objects...")
    clear_all_mesh_and_empty_objects()
    
    # Setup render
    setup_render_settings()
    
    # Import XYZ file
    print(f"Importing: {test_file.name}")
    try:
        bpy.ops.import_mesh.xyz(filepath=str(test_file))
    except Exception as e:
        print(f"Error importing: {e}")
        return
    
    # Get structure bounds
    center, size, max_dim = get_scene_bounds()
    print(f"\nStructure bounds:")
    print(f"  Center: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})")
    print(f"  Size: ({size[0]:.2f}, {size[1]:.2f}, {size[2]:.2f}) A")
    print(f"  Max dimension: {max_dim:.2f} A")
    
    # Apply metallic materials
    print("\nApplying metallic materials:")
    make_all_materials_metallic()
    
    # Create PBC lines
    print("\nCreating PBC unit cell:")
    if poscar_file:
        lattice = parse_lattice_from_poscar(poscar_file)
        create_pbc_lines(lattice, line_radius=0.03)
    else:
        print("  Skipping PBC - no POSCAR file")
    
    print_all_objects()
    
    # Setup lights
    print("\nSetting up lights:")
    setup_lights(center, max_dim)
    
    # Render angled view
    print("\nRendering angled view:")
    setup_camera_perspective(center, max_dim)
    output_path = output_dir / f"{test_file.stem}_angled.png"
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {output_path}")
    
    # Render top view
    print("\nRendering top view:")
    setup_camera_top(center, max_dim)
    output_path = output_dir / f"{test_file.stem}_top.png"
    bpy.context.scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {output_path}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
