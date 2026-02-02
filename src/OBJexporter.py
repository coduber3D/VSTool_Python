def export_obj(mesh, file_path):
    """
    Export a mesh to Wavefront OBJ format.

    mesh must have:
      - positions: [x, y, z, ...]
      - uvs: [u, v, ...]
      - normals: [x, y, z, ...]
      - indices: [i0, i1, i2, ...]
    """

    with open(file_path, "w") as f:
        f.write("# Exported OBJ\n")

        # ----------------------------------
        # Write vertex positions
        # ----------------------------------
        for i in range(0, len(mesh.positions), 3):
            x, y, z = mesh.positions[i:i+3]
            f.write(f"v {x} {y} {z}\n")

        # ----------------------------------
        # Write texture coordinates (UVs)
        # OBJ uses (u, v) with v flipped
        # ----------------------------------
        for i in range(0, len(mesh.uvs), 2):
            u, v = mesh.uvs[i:i+2]
            f.write(f"vt {u} {1.0 - v}\n")

        # ----------------------------------
        # Write normals
        # ----------------------------------
        for i in range(0, len(mesh.normals), 3):
            nx, ny, nz = mesh.normals[i:i+3]
            f.write(f"vn {nx} {ny} {nz}\n")

        # ----------------------------------
        # Write faces
        # OBJ indices are 1-based!
        # ----------------------------------
        for i in range(0, len(mesh.indices), 3):
            i1 = mesh.indices[i] + 1
            i2 = mesh.indices[i + 1] + 1
            i3 = mesh.indices[i + 2] + 1

            # f v/vt/vn
            f.write(f"f {i1}/{i1}/{i1} {i2}/{i2}/{i2} {i3}/{i3}/{i3}\n")