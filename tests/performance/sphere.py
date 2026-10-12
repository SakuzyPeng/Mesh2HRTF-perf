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
