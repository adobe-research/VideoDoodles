import os
import sys
import time

import numpy as np

from .convert import get_default_position_at
from .tracking_orientation import optimize_frames
from .tracking_position import find_motion_path, optimize_trajectory
from .utils import orientation_slerp

try:
    width = os.get_terminal_size().columns 
except:
    width = 20

def find_positions(clip, camera_data, position_keyframes, segments, previous_state):
    print("-" * width)
    print("POSITIONS SOLVE")

    start = time.time()

    position_keyframes = [kf for kf in position_keyframes if ("pos_3d" in kf.keys()) or ("pos_2d" in kf.keys())]

    down_scale_factor = camera_data["down_scale_factor"]

    # Initialize with data from previous state
    soft_velocity_cstr = previous_state["velocities"]
    initial_positions = previous_state["positions"]

    is_presolved = np.zeros(len(soft_velocity_cstr), dtype=bool)

    kf_indices = np.array([kf['t'] for kf in position_keyframes])

    # Form contiguous segments that require 3D tracking:
    tracking_segments = []

    for segment in segments:
        idx_range = np.arange(segment["start"], segment["end"] + 1)
        if not segment["dirty"]:
            print("Skipping indices (no update):", idx_range)
            continue
        if len(idx_range) > 0:
            print(f"Considering subproblem for indices: [{segment['start']}, {segment['end']}]")
            # Find path in motion graph for given keyframes
            if (segment["mode"] == 0):
                print("Will do linear interpolation")
                start_t = idx_range[0]
                end_t = idx_range[-1]
                kf_is_present = np.isin(kf_indices, [start_t, end_t])
                if (np.count_nonzero(kf_is_present) == 0):
                    print("Error: Range does not have endpoint keyframes, can't interpolate.")
                    traj_range = np.tile(np.zeros(3), len(idx_range)).reshape((-1, 3))
                elif (np.count_nonzero(kf_is_present) == 1):
                    ref_kf_idx = np.flatnonzero(kf_is_present).item()
                    ref_kf = position_keyframes[ref_kf_idx]
                    constant_pos = get_default_position_at(ref_kf, clip)
                    traj_range = np.tile(constant_pos, len(idx_range)).reshape((-1, 3))
                else:
                    # Interpolate from start to end
                    endpoint_kf_indices = np.flatnonzero(kf_is_present)
                    start_kf = position_keyframes[endpoint_kf_indices[0]]
                    end_kf = position_keyframes[endpoint_kf_indices[1]]
                    start_pos = get_default_position_at(start_kf, clip)
                    end_pos = get_default_position_at(end_kf, clip)
                    traj_range = np.empty((0, 3))
                    for t in idx_range:
                        u = (t - start_t) / (end_t - start_t)
                        pos_t = start_pos * (1 - u) + end_pos * u
                        traj_range = np.row_stack([traj_range, pos_t])
                # Update the soft_velocity_cstr and initial_positions because they are reused in other stuff
                soft_velocity_cstr[idx_range[:-1]] = traj_range[1:] - traj_range[:-1]
                soft_velocity_cstr[idx_range[-1]] = traj_range[-1] - traj_range[-2]

                initial_positions[idx_range] = traj_range

                is_presolved[idx_range] = True
            else:
                # Register that this index range requires tracking:
                # (we create contiguous index ranges to solve each contiguous range in one go)
                if len(tracking_segments) > 0 and tracking_segments[-1][-1] == idx_range[0]:
                    tracking_segments[-1] = np.append(tracking_segments[-1], idx_range[1:])
                else:
                    tracking_segments.append(idx_range)
                    
    for idx_range in tracking_segments:
        # - Select keyframes
        # Keep only keyframe that are in range
        kf_mask = np.isin(kf_indices, idx_range)
        position_keyframes_subset = np.array(position_keyframes)[kf_mask]

        print("-" * (width // 2))
        print("Solving tracking for indices:", idx_range)
        print("with keyframes:", position_keyframes_subset)


        initial_positions_i, soft_velocity_cstr_i = find_motion_path(
            clip, 
            position_keyframes_subset, 
            prune_nodes=0.9,
            feature_similarity_weight=0,
            targets_feature_similarity_weight=0.0,
            proximity_weight=1.0,
            first_frame_idx=idx_range[0],
            last_frame_idx=idx_range[-1])

        soft_velocity_cstr[idx_range] = soft_velocity_cstr_i
        initial_positions[idx_range] = initial_positions_i

    print(f"Motion graph search time (all segments): {time.time() - start}")
    

    # Optimize trajectory
    start_opt = time.time()
    pts_opt = optimize_trajectory(clip, position_keyframes, soft_velocity_cstr, initial_positions, is_presolved)
    # pts_opt = initial_positions

    pts_opt /= down_scale_factor
    print(f"Trajectory optimization time: {time.time() - start_opt}")


    # For orientation opt
    # all_velocities = nodes_data[:, 3:6]
    velocity_scale = np.quantile(np.linalg.norm(soft_velocity_cstr, axis = 1), 0.9)
    if velocity_scale < 1e-4:
        matching_weights = np.zeros(len(soft_velocity_cstr))
    # normalized_velocities = normalize(soft_velocity_cstr)
    else:
        matching_weights = np.clip(np.linalg.norm(soft_velocity_cstr, axis = 1) / velocity_scale, 0, 1)

    print(f"Overall time trajectory optimization: {time.time() - start}")


    return pts_opt, soft_velocity_cstr, matching_weights


def find_orientations(orientation_keyframes, target_vectors, matching_weights, segments):
    print("-" * width)
    print("ORIENTATIONS SOLVE")

    stride = 5

    # target_vectors = normalize(target_vectors)

    # print(target_vectors)
    # print(matching_weights)

    opt_frames_per_range = []

    orientation_keyframes = [kf for kf in orientation_keyframes if "rot_mat" in kf.keys()]
    kf_indices = np.array([kf['t'] for kf in orientation_keyframes])

    for segment in segments:
        idx_range = np.arange(segment["start"], segment["end"] + 1)
        if segment["dirty"] and len(idx_range) > 0:
            print(f"Considering subproblem for indices: [{segment['start']}, {segment['end']}]")
             # Find path in motion graph for given keyframes
            if (segment["mode"] == 0 or len(idx_range) == 2):
                print("Will do slerp")
                start_t = idx_range[0]
                end_t = idx_range[-1]
                kf_is_present = np.isin(kf_indices, [start_t, end_t])
                if (np.count_nonzero(kf_is_present) == 0):
                    print("Error: Range does not have endpoint keyframes, can't interpolate.")
                    opt_frames_i = np.tile(np.eye(3), (len(idx_range), 1, 1))
                elif (np.count_nonzero(kf_is_present) == 1):
                    ref_kf_idx = np.flatnonzero(kf_is_present).item()
                    ref_kf = orientation_keyframes[ref_kf_idx]
                    constant_rot = ref_kf["rot_mat"]
                    opt_frames_i = np.tile(constant_rot, (len(idx_range), 1, 1))
                else:
                    endpoint_kf_indices = np.flatnonzero(kf_is_present)
                    start_kf = orientation_keyframes[endpoint_kf_indices[0]]
                    end_kf = orientation_keyframes[endpoint_kf_indices[1]]
                    opt_frames_i = orientation_slerp([start_kf, end_kf], start_frame=segment["start"], end_frame=segment["end"])
            else:
                target_i = target_vectors[idx_range]
                matching_weights_i = matching_weights[idx_range]

                kf_indices = np.array([kf['t'] for kf in orientation_keyframes])
                kf_orientations = np.array([kf['rot_mat'] for kf in orientation_keyframes])

                # Keep only keyframe that are in range and reindex them
                kf_mask = np.isin(kf_indices, idx_range)
                kf_indices = kf_indices[kf_mask]
                # print("original kf indices", kf_indices)
                kf_indices = np.searchsorted(idx_range, kf_indices)
                kf_orientations = kf_orientations[kf_mask]

                # print("remapped kf indices", kf_indices)
                print("Solving orientation tracking for indices:", idx_range)

                opt_frames_i, segment_id, relative_frames = optimize_frames(
                    target_i, 
                    matching_weights_i, 
                    kf_indices,
                    kf_orientations,
                    discontinuity_threshold=0.2,
                    W_match=1, W_smooth=10,
                    stride=stride,
                    quiet=True)
        else:
            print("Skipping indices (no update):", idx_range)
            opt_frames_i = np.array([])

        opt_frames_per_range.append(opt_frames_i)

    # print(pts_opt)

    # status = 1 # found


    return opt_frames_per_range