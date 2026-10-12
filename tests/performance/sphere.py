"""Synthetic octahedral sphere mesh. EUPL-1.2, 2026-10-12."""
import numpy as np


def sphere_mesh(subdivisions=3):
    vertices = [np.array(v, float) for v in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]]
    faces = [(x,y,z) for x in [0,1] for y in [2,3] for z in [4,5]]
    for _ in range(subdivisions):
        cache, out = {}, []
        def mid(a,b):
            key = tuple(sorted((a,b)))
            if key not in cache:
                p = vertices[a]+vertices[b]
                cache[key] = len(vertices)
                vertices.append(p/np.linalg.norm(p))
            return cache[key]
        for a,b,c in faces:
            ab,bc,ca = mid(a,b),mid(b,c),mid(c,a)
            out.extend([(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)])
        faces = out
    vertices, faces = np.array(vertices), np.array(faces)
    for i, face in enumerate(faces):
        p = vertices[face]
        if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),p.mean(axis=0))<0:
            faces[i] = face[[0,2,1]]
    return vertices,faces


def mixed_mesh(divisions=8):
    """Closed cube-sphere with both triangles and bilinear quadrilaterals."""
    vertices, faces, indices = [], [], {}
    for axis in range(3):
        other = [i for i in range(3) if i != axis]
        for side in (-1, 1):
            grid = {}
            for u in range(divisions + 1):
                for v in range(divisions + 1):
                    point = np.zeros(3)
                    point[axis] = side
                    point[other] = [-1 + 2*u/divisions, -1 + 2*v/divisions]
                    point /= np.linalg.norm(point)
                    key = tuple(np.round(point, 12))
                    if key not in indices:
                        indices[key] = len(vertices)
                        vertices.append(point)
                    grid[u, v] = indices[key]
            for u in range(divisions):
                for v in range(divisions):
                    face = [grid[u, v], grid[u+1, v], grid[u+1, v+1], grid[u, v+1]]
                    points = np.array([vertices[i] for i in face])
                    if np.dot(np.cross(points[1]-points[0], points[2]-points[0]), points.mean(axis=0)) < 0:
                        face.reverse()
                    if (axis + u + v) % 2:
                        faces.extend((face[:3], [face[0], face[2], face[3]]))
                    else:
                        faces.append(face)
    return np.array(vertices), faces
