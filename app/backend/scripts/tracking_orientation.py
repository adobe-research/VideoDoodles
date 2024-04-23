import math
import time

import numpy as np
import pymanopt
import torch
from pymanopt.manifolds import SpecialOrthogonalGroup
from pymanopt.optimizers import SteepestDescent, TrustRegions
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp

from .utils import normalize


def skew(M):
    return (M - torch.transpose(M, 1, 2)) * 0.5


def create_cost_and_derivates(manifold, vs, matching_weights, smoothing_weights, kf_rots, kf_indices, index_ranges=None, W_match=1, W_smooth=1):
    # keyframes MUST be sorted by frame index

    vs_ = torch.tensor(vs, requires_grad=False)
    matching_weights_ = torch.tensor(matching_weights, requires_grad=False)
    smoothing_weights_ = torch.tensor(smoothing_weights, requires_grad=False)

    kf_rots_ = [torch.tensor(r, requires_grad=False) for r in kf_rots]

    @pymanopt.function.pytorch(manifold)
    # @my_decorator(manifold)
    def cost(vars):
        # Separate vars
        match_targets = 0
        if index_ranges is None or len(index_ranges) == 1:
            R_base = vars[0]
            X = vars[1:]
            # dTarget = X @ R_base - As_
            dT = (X @ R_base)[:, :, 0] - vs_
            match_targets = torch.sum(matching_weights_[:,None] * dT * dT)
        else:
            X = vars[len(index_ranges):]
            for i, idx_range in enumerate(index_ranges):
                R_base_i = vars[i]
                # dTarget_i = X[idx_range] @ R_base_i - As_[idx_range]
                dT = (X[idx_range] @ R_base_i)[:, :, 0] - vs_[idx_range]
                match_targets += torch.sum(matching_weights_[idx_range, None] * dT * dT)

        # Insert fixed keyframed rotations
        for idx, rot in zip(kf_indices, kf_rots_):
            X = torch.cat([X[:idx], rot[None,], X[idx:]])


        dX = X[1:] - X[:-1]

        smoothness = torch.sum(smoothing_weights_ * torch.sum(dX * dX, axis=(1,2)))
        d2_gamma = skew(torch.transpose(X[1:-1], 1, 2) @ (X[2:] + X[:-2]))
        # smoothness_2 = torch.sum(smoothing_weights_**3 * torch.sum(d2_gamma * d2_gamma))
        return W_match * match_targets + W_smooth * smoothness #+ W_smooth * smoothness_2


    # else:
    #     raise ValueError(f"Unsupported backend '{backend}'")

    return cost


def stride_select(N, stride, must_keep=None, preserve_endpoints=True):
    mask = np.zeros(N, dtype=bool)
    mask[np.arange(math.ceil(N / stride)) * stride] = True
    if must_keep is not None:
        mask[must_keep] = True
    if preserve_endpoints:
        mask[0] = True
        mask[-1] = True

    return mask, get_mapping(mask)

def get_mapping(mask):
    selected_N = np.count_nonzero(mask)
    mapping = np.ones(len(mask), dtype=int) * -1
    mapping[mask] = np.arange(selected_N)

    return mapping

def get_closest_aligned_frame(vector, initial_frame):
    # Returns an orthogonal frame (u, v, w) that aligns with vector (u = vector)
    # and the rotation that transforms the initial frame to the vector aligned frame

    # - Find the axis that's closest to vector
    axis_match_score = np.sum(initial_frame.T * vector, axis = 1)
    matching_axis = np.argmax(np.abs(axis_match_score))

    u = vector

    # - Compute other axes
    # Next axis is computed as 
    next_axis = initial_frame[:, (matching_axis + 1) % 3]
    v = np.cross(u, np.cross(next_axis, u))
    # Last axis is u x v
    w = np.cross(u, v)

    aligned_frame = np.column_stack([u, v, w])

    # base_rotation: initial_frame @ base_rotation = aligned_frame
    base_rotation = initial_frame.T @ aligned_frame

    return aligned_frame, base_rotation

def initialize(keyframe_indices, keyframe_rots, N):
    # First find initial rotations for all frames
    # If no keyframes: Identity
    if len(keyframe_indices) == 0:
        init_rots = np.tile(np.eye(3), (N, 1, 1))
    elif len(keyframe_indices) == 1:
        init_rots = np.tile(keyframe_rots[0], (N, 1, 1))
    # Otherwise: slerp of keyframes
    else:
        key_rots = R.from_matrix(keyframe_rots)
        slerp = Slerp(keyframe_indices, key_rots)

        first_kf = np.min(keyframe_indices)
        last_kf = np.max(keyframe_indices)

        interp_rots = slerp(np.arange(first_kf, last_kf + 1)).as_matrix()

        # Pad beginning and end
        if (first_kf) > 0:
            start_pad_mats = np.tile(interp_rots[0], (first_kf, 1, 1))
            interp_rots = np.row_stack([start_pad_mats, interp_rots])
        if (last_kf) < N - 1:
            end_pad_mats = np.tile(interp_rots[-1], (N - 1 - last_kf, 1, 1))
            interp_rots = np.row_stack([interp_rots, end_pad_mats])

        init_rots = interp_rots

    return init_rots


def initialize_base_rots(initial_rots, target_vectors, index_ranges):
    # print(len(index_ranges))
    # return np.tile(np.eye(3), (len(index_ranges),1,1))
    init_base_rots = np.empty((0, 3, 3))
    for idx_range in index_ranges:
        # Set the base rot as shortest relative rotation between target vector and initial matrix at this frame
        start_idx = idx_range[0]
        target_vec = target_vectors[start_idx]
        init_rot = initial_rots[start_idx]

        aligned_frame, base_rot = get_closest_aligned_frame(target_vec, init_rot)
        init_base_rots = np.vstack([init_base_rots, base_rot.reshape(1, 3, 3)])

    return init_base_rots

def optimize_frames(
    target_vectors, 
    matching_weights, 
    keyframe_indices,
    keyframe_orientations, 
    discontinuity_threshold=0.2, 
    W_match=1, W_smooth=1, 
    stride=2,
    quiet=False):

    stride = stride if (len(target_vectors) > stride + 1) else 1
    # Detect discontinuities in target vectors
    target_vectors = normalize(target_vectors)
    vecs_dist = 1 - np.abs(np.sum(target_vectors[1:]*target_vectors[:-1], axis = 1))
    # print(vecs_dist)
    
    # Detect discontinuities in the trajectory: we use a simple heuristic by checking when the velocity vector has a small norm
    discontinuous_frames_idx = np.flatnonzero(matching_weights < discontinuity_threshold)

    # print("Discontinuity in target vectors:", discontinuous_frames_idx)

    # Ensure it is sorted correctly
    sorted_kf = np.argsort(keyframe_indices)
    keyframe_indices = np.array(keyframe_indices, dtype=int)[sorted_kf]
    keyframe_orientations = keyframe_orientations[sorted_kf]

    # Keep only frames at given stride interval
    # (we solve for a subset of frames to speed things up, intermediate frames are obtained by interpolation)
    N_initial = len(target_vectors)
    to_keep = np.unique(np.concatenate([keyframe_indices, discontinuous_frames_idx]))
    stride_mask, mapping = stride_select(len(target_vectors), stride, to_keep if len(to_keep) > 0 else None)
    target_vectors = target_vectors[stride_mask]
    matching_weights = matching_weights[stride_mask]
    if len(keyframe_indices) > 0:
        keyframe_indices = mapping[keyframe_indices]
    if len(discontinuous_frames_idx) > 0:
        discontinuous_frames_idx = mapping[discontinuous_frames_idx]

    # print("remapped kf indices", keyframe_indices)

    # Compute smoothing weights depending on the distance between frames (after applying stride selection)
    inverse_stride_mapping = np.flatnonzero(stride_mask)
    smoothing_weights = 1.0 / (inverse_stride_mapping[1:] - inverse_stride_mapping[:-1])


    initial_rots = initialize(keyframe_indices, keyframe_orientations, len(target_vectors))

    # Keep only non keyframed frames
    if len(keyframe_indices) > 0:
        is_keyframed = np.zeros(len(target_vectors), dtype=bool)
        is_keyframed[keyframe_indices] = True
        not_keyframed = np.logical_not(is_keyframed)
        target_vectors = target_vectors[not_keyframed]
        matching_weights = matching_weights[not_keyframed]
        initial_rots = initial_rots[not_keyframed]
        if len(discontinuous_frames_idx) > 0:
            discontinuous_frames_idx = get_mapping(not_keyframed)[discontinuous_frames_idx]
    
    # We introduce rotation offsets (R* in the paper, Eq. 3)
    # Each trajectory segment has its own R* (which we call "base_rot")
    # segments are determined based on detected discontinuities in the trajectory
    index_ranges = []

    if len(discontinuous_frames_idx) > 0:
        min_zone_size = 3

        for i in range(0, len(discontinuous_frames_idx)):
            idx_start = 0 if (i == 0) else discontinuous_frames_idx[i-1]
            idx_end = len(target_vectors) if i == (len(discontinuous_frames_idx) - 1) else discontinuous_frames_idx[i]
            idx_range = np.arange(idx_start, idx_end)
            if (idx_end - idx_start >= min_zone_size):
                index_ranges.append(idx_range)
    else:
        index_ranges.append(np.arange(len(target_vectors)))
    # print("index ranges", index_ranges)
    n_base_rots = len(index_ranges)

    # SO3
    n = 3
    # For k rotations (nb of frames + nb of rotation offsets R*)
    k = len(target_vectors) + n_base_rots

    manifold = SpecialOrthogonalGroup(n, k=k)

    torch.autograd.set_detect_anomaly(True)

    cost = create_cost_and_derivates(
        manifold, target_vectors, matching_weights, smoothing_weights, keyframe_orientations, keyframe_indices, index_ranges, W_match, W_smooth
    )
    problem = pymanopt.Problem(
        manifold, cost
    )

    converged_grad_norm = 1e-06
    optimizer = TrustRegions(verbosity=2 * int(not quiet), max_time=40, min_gradient_norm=converged_grad_norm)

    init_base_rots = initialize_base_rots(initial_rots, target_vectors, index_ranges)
    all_initial_rots = np.vstack([init_base_rots, initial_rots])

    start_time = time.time()
    print(f"Starting orientation optimization for {len(target_vectors)} frames and {n_base_rots} rotation offsets. This can take some time to complete...")

    res = optimizer.run(problem, initial_point=all_initial_rots, maxinner=manifold.dim*3)

    print(f"Orientation optimizer run time = {(time.time() - start_time):02f}s")

    if res.gradient_norm > converged_grad_norm:
        X = all_initial_rots
        print("Optimization is too slow => fall back to interpolation.")
    else:
        X = res.point

    rots = X[n_base_rots:]
    base_rots = X[:n_base_rots]

    segment_id = np.ones(len(rots), dtype=int) * -1

    for idx, idx_range in enumerate(index_ranges):
        segment_id[idx_range] = idx

    # Insert fixed keyframed rotations
    for idx, rot in zip(keyframe_indices, keyframe_orientations):
        rots = np.concatenate([rots[:idx], rot[None,], rots[idx:]])
        segment_id = np.concatenate([segment_id[:idx], np.array([-1]), segment_id[idx:]])

    # Find rest of the orientation by interpolation
    if stride > 1 :
        fixed_rots = R.from_matrix(np.array(rots))
        fixed_times = np.arange(N_initial)[stride_mask]
        slerp = Slerp(fixed_times, fixed_rots)
        rots = slerp(np.arange(N_initial)).as_matrix()

        # Complete index_ranges
        full_segment_id = np.ones(N_initial, dtype=int) * -1
        full_segment_id[stride_mask] = segment_id
        segment_id = full_segment_id

    return rots, segment_id, base_rots


