import json
import numpy as np
import os
from pathlib import Path

from .read_scene_data import get_3D_point
from .paths import backend_data_root_folder

def windowing_matrix(hres, vres, y_up=True):
    if y_up:
        return np.array([
        [ hres/2,  0, hres/2],
        [ 0,  -vres/2, vres/2],
        [0, 0, 1]
        ], dtype=float)
    else:
        return np.array([
        [ hres/2,  0, hres/2],
        [ 0,  vres/2, vres/2],
        [0, 0, 1]
        ], dtype=float)

def openGL_projection_matrix_to_cv_intrinsics(M, hres, vres):
    windowing_mat = windowing_matrix(hres, vres)

    M_cv = np.delete(np.delete(M, 2, axis=0), 3, axis = 1)

    K = windowing_mat @ M_cv

    return K

# CAUTION: Here we assume that K has axes in OpenGL standard (right-handed, -z forward, y up)
def cv_intrinsics_to_openGL_projection_matrix(K, hres, vres, near=0.1, far=10, y_up=True):
    dimensionless_K = np.linalg.inv(windowing_matrix(hres, vres, y_up)) @ K
    gamma = - (far + near) / (far - near)
    beta = -2 * near * far / (far - near)
    dimensionless_K[2, 2] = gamma
    M_gl = np.insert(np.insert(dimensionless_K, 3, [0, 0, -1], axis = 0), 3, [0, 0, beta, 0], axis = 1)
    return M_gl

def parse_trajectory_data(data):
    mvt_type = data["type"]
    video_name = data["clip"]
    keyframes = data["keyframes"]
    position_segments = data["positionSegments"]
    orientation_segments = data["orientationSegments"]

    # Load data associated with this video
    camera_data = np.load(os.path.join(backend_data_root_folder, video_name, "cameras.npz"))

    res = camera_data["res"]

    qs = []
    times = []

    clip_length = len(camera_data["Ks"])

    position_kfs = []
    orientation_kfs = []

    for kf in keyframes:
        frame_idx = kf["time"]
        props = kf["props"]

        pos_kf = {'t': frame_idx}
        rot_kf = {'t': frame_idx}


        if "x" in props.keys() and "y" in props.keys():
            x = props["x"]
            y = props["y"]

            q = np.array([x, y], dtype=float)

            pos_kf['pos_2d'] = q

        if "depth" in props.keys():
            # From 2D position and depth, unproject to 3D using an OpenGL projection matrix and RT
            proj_matrix = cv_intrinsics_to_openGL_projection_matrix(camera_data["Ks"][frame_idx], res[0], res[1], near=camera_data["near"], far=camera_data["far"])
            # Put x and y into [-1, 1] NDC
            x_ndc = x * 2 - 1
            # in screen space, y points down, in NDC, y points up
            y_ndc = -y * 2 + 1
            pt_ndc = np.array([x_ndc, y_ndc, props["depth"], 1], dtype=float)
            # R = camera_data["RTs"][frame_idx][:3, :3].T
            # t = -R @ camera_data["RTs"][frame_idx][:3, 3]
            R = camera_data["Rs"][frame_idx]
            t = camera_data["ts"][frame_idx]
            pt_unproj = np.linalg.inv(proj_matrix) @ pt_ndc
            pt_unproj /= pt_unproj[3]
            pt_3d = R @ pt_unproj[:3] + t
            pos_kf['pos_3d'] = pt_3d * camera_data["down_scale_factor"] # All subsequent operations are in default (unscaled) space

        if "rot" in props.keys():
            rot_kf["rot_mat"]= np.array(props["rot"]["elements"]).reshape((4,4)).T[:3, :3]

        if ("pos_3d" in pos_kf.keys()) or ("pos_2d" in pos_kf.keys()):
            position_kfs.append(pos_kf)
        if ("rot_mat" in rot_kf.keys()):
            orientation_kfs.append(rot_kf)

    # Sort keyframes by frame index (we will assume that keyframes are well sorted in subsequent processing)
    position_kfs = np.array(position_kfs)[np.argsort([kf['t'] for kf in position_kfs])]
    orientation_kfs = np.array(orientation_kfs)[np.argsort([kf['t'] for kf in orientation_kfs])]

    print("position keyframes:", position_kfs)
    print("orientation keyframes:", orientation_kfs)

    # Sort segments
    position_segments = np.array(position_segments)[np.argsort([segment['start'] for segment in position_segments])]
    orientation_segments = np.array(orientation_segments)[np.argsort([segment['start'] for segment in orientation_segments])]

    return mvt_type, video_name, clip_length, camera_data, position_kfs, orientation_kfs, position_segments, orientation_segments

def get_default_position_at(kf, clip):
    if "pos_3d" in kf.keys():
        # Just set the whole trajectory to be that position
        pt_3d = kf["pos_3d"]
    else:
        # Infer position based on depth at this pixel
        kf_pos_2d = np.clip(kf['pos_2d'], [0, 0], [1, 1])
        pt_3d = get_3D_point(clip, kf_pos_2d, kf['t'], 1, 1)

    return pt_3d

def get_update_free_zones(segments, clip_length):

    traj_pt_needs_update = np.zeros(clip_length, dtype=bool)
    for segment in segments:
        segment_range = np.arange(segment["start"], segment["end"] + 1)
        if segment['dirty']:
            traj_pt_needs_update[segment_range] = True

    frames_that_dont_need_update = np.flatnonzero(~traj_pt_needs_update)

    print("Unchanged frames (not updating)", frames_that_dont_need_update)

    return frames_that_dont_need_update



def jsonize(keyframes):
    json_keyframes = []
    for kf in keyframes:
        json_kf = {}
        for prop in kf.keys():
            if type(kf[prop]).__module__ == 'numpy':
                # Convert to list
                json_kf[prop] = kf[prop].tolist()
            else:
                json_kf[prop] = kf[prop]
        json_keyframes.append(json_kf)
    return json_keyframes

def dejsonize(keyframes):
    kfs = []
    for kf in keyframes:
        json_kf = {}
        for prop in kf.keys():
            if type(kf[prop]) is list:
                # Convert to numpy
                json_kf[prop] = np.array(kf[prop])
            else:
                json_kf[prop] = kf[prop]
        kfs.append(json_kf)
    return kfs