import os
import time
from typing import List, Tuple

import numpy as np
from scipy.sparse import bmat, csr_matrix
from scipy.sparse.csgraph import shortest_path
from scipy.sparse.linalg import spsolve

from .paths import backend_data_root_folder
from .read_scene_data import (get_features, get_features_dims, get_flows,
                              get_maps_dims, get_positions, index_into_data)
from .utils import (compute_all_edge_weights, get_camera_ray, mse_mat,
                    sparse_add_value)


def find_motion_path(
      video_name                       : str,
      keyframes                        : List[dict],
      proximity_weight                 : float = 1,
      feature_similarity_weight        : float = 0,
      targets_feature_similarity_weight: float = 0,
      prune_nodes                      : float = 0.9,
      prune_edges                      : float = 0,
      first_frame_idx                  : int   = None,
      last_frame_idx                   : int   = None
    ) -> Tuple[np.ndarray, np.ndarray] : 
    '''
    Finds the shortest path through the "video volume", the directed graph that connects each pixel in frame t to every pixel in frame t+1.
    This corresponds to what is described in the paragraph "Tracking 3D positions" in Sec. 5.2 of the paper.
    The default arguments are those used in the results/evaluations.

    Args:
        video_name (str)
        keyframes (List[dict]): list of keyframes sorted by time (caution: the fact that they are sorted is assumed)
        proximity_weight (float, optional): weight of the 3D distance term in the optimization. Defaults to 1.
        feature_similarity_weight (float, optional): weight of the image feature term (between nodes) in the optimization. Defaults to 0.
        targets_feature_similarity_weight (float, optional): weight of the image feature term (between a node and target keyframes) in the optimization. Defaults to 0.
        prune_nodes (float, optional): Prune the X% lowest weight nodes at each frame (based on similarity with the best matching keyframe). Defaults to 0.9.
        prune_edges (float, optional):Prune the X% lowest weight edges. Set to 0 to deactivate pruning. Defaults to 0.
        first_frame_idx (int, optional): frame at which to start tracking. Defaults to None (meaning we start at frame 0).
        last_frame_idx (int, optional): frame at which to end tracking. Defaults to None (meaning we end at the last frame of the video).

    Returns:
        motion_path_3D_positions (np.ndarray): a (T, 3) array of 3D vectors corresponding to the 3D position of points along the trajectory at each of the T video frames
        motion_path_3D_flows (np.ndarray): a (T, 3) array of 3D vectors corresponding to the 3D flow at points along the trajectory at each of the T video frames
    '''     

    # print(proximity_weight, feature_similarity_weight, targets_feature_similarity_weight)

    # print(f"memory start: {Process().memory_info().rss:e}")

    # Filter out keyframes that don't contain position data
    keyframes = [kf for kf in keyframes if ("pos_3d" in kf.keys()) or ("pos_2d" in kf.keys())]

    # Data folders

    start_loading_data = time.time()


    total_nb_frames, maps_res_x, maps_res_y = get_maps_dims(video_name)
    maps_res = (maps_res_x, maps_res_y)
    masks_archive = np.load(os.path.join(backend_data_root_folder, video_name, "masks.npz"))
    masks = masks_archive["masks"]

    flow_3d_archive = get_flows(video_name, total_nb_frames, maps_res)
    pos_3d_archive = get_positions(video_name, total_nb_frames, maps_res)
    # print(flow_3d_archive.shape, pos_3d_archive.shape)

    print(f"Time to load all data = {time.time() - start_loading_data:.2f}s")
    # print(f"memory after load (3d maps): {Process().memory_info().rss:e}")

    # Number of frames in the video?
    if first_frame_idx is None:
        first_frame_idx = 0
    if last_frame_idx is None:
        last_frame_idx = len(pos_3d_archive) - 1
    total_nb_frames = last_frame_idx - first_frame_idx + 1

    # If we need videowalk features, load the pre-computed feature maps
    s = time.time()
    T, res_x, res_y, d_feat = get_features_dims(video_name)
    # print("feature maps dim", T, res_x, res_y, d_feat)
    all_frames_features = get_features(video_name, T, (res_x, res_y), d_feat)
    print(f"Time to load features = {time.time() - s:.4f}s")
    # print(f"memory after load (feature maps): {Process().memory_info().rss:e}")

    # print("nb frames, res_x, res_y", total_nb_frames, res_x, res_y)

    # Compute image features at each keyframe
    max_feature_cost = 1e4
    match_best_kf_feature_cost = np.ones((all_frames_features.shape[0], all_frames_features.shape[1]), dtype=all_frames_features.dtype) * max_feature_cost
    keyframe_times = np.array([kf["t"] for kf in keyframes])
    keyframe_by_time = {}
    nb_of_keyframe_influence = np.zeros(all_frames_features.shape[0])
    for kf_idx, kf in enumerate(keyframes):
        start = time.time()
        kf_pos = kf["pos_2d"]
        kf_time = kf["t"]
        keyframe_by_time[kf_time] = kf

        kf_flat_idx = index_into_data(kf_pos.reshape(1, 2), (1, 1), (res_x, res_y)).item()
        kf_desc = all_frames_features[kf_time, kf_flat_idx]

        # Find out start/end of keyframe influence zone
        start_frame_idx = first_frame_idx if kf_idx == 0 else (keyframe_times[kf_idx - 1] + 1)
        end_frame_idx = last_frame_idx if kf_idx == (len(keyframes) - 1) else (keyframe_times[kf_idx + 1] - 1)

        nb_of_keyframe_influence[start_frame_idx:end_frame_idx+1] += 1

        # Compute L2 norm between all_frame_features and kf_desc
        start_test = time.time()
        match_kf_feature_cost = np.zeros((end_frame_idx + 1 - start_frame_idx, all_frames_features.shape[1]))
        for t in range(start_frame_idx, end_frame_idx + 1):
            match_kf_feature_cost[t - start_frame_idx] = mse_mat(all_frames_features[t], kf_desc.reshape((1, -1))).flatten()
        # print(f"Time computing mse : {time.time() - start_test}")

        # Keep the lowest cost per pixel
        match_best_kf_feature_cost[start_frame_idx:end_frame_idx+1] = np.minimum(match_best_kf_feature_cost[start_frame_idx:end_frame_idx+1], match_kf_feature_cost)

        print(f"Time computing per node cost for kf {kf_time} : {time.time() - start:.2f}s")


    start_graph_weights = time.time()

    # Data about nodes
    # - frame time
    # - 2D pos (x, y) in pixels
    nodes_2d_positions = np.empty((0, 2), dtype=int)

    source_dst_indices = []
    sink_src_indices = []

    # store data of previous frame's nodes to compute edge weights
    prev_frame_nodes_data = {}

    current_node_idx = 0
    current_nz_data_idx = 0


    N_samples = int((res_x * res_y) * (1 - prune_nodes))
    nb_edges_to_prune = int(prune_edges * N_samples)
    # print("pruning edges:", nb_edges_to_prune, "/", N_samples)
    N_samples_dest = N_samples - nb_edges_to_prune

    non_keyframed_frames_count = total_nb_frames - len(keyframes)

    if non_keyframed_frames_count == 0:
        # The shortest path is just the keyframes
        shortest_path_2d_positions = np.empty((0, 2), dtype=int)

        for kf in keyframes:
            kf_pos = (np.round(kf["pos_2d"] * np.array([res_x, res_y]))).astype(int)
            shortest_path_2d_positions = np.row_stack([shortest_path_2d_positions, kf_pos])

    else:
        # Total number of nodes in the graph: nb_frames * nb_samples_per_frame + nb_keyframes + 2 (source/sink)
        graph_dim = N_samples * non_keyframed_frames_count + len(keyframes) + 2

        source_idx = graph_dim - 2
        sink_idx = graph_dim - 1

        # non-zero values: (dense samples => samples) * (nb connections)
        # nb connections = (nb_frames - 1) => (remove connections on both sides of frames with keyframes)
        nb_keyframe_src = np.count_nonzero(keyframe_times < last_frame_idx)
        nb_keyframe_dst = np.count_nonzero(keyframe_times > first_frame_idx)

        # Count adjacent keyframes
        keyframe_time_diff = keyframe_times[1:] - keyframe_times[:-1]
        nb_kf_kf_connexions = np.count_nonzero(keyframe_time_diff == 1)

        # print("keyframe => keyframe", nb_kf_kf_connexions)

        nb_keyframe_src -= nb_kf_kf_connexions
        nb_keyframe_dst -= nb_kf_kf_connexions

        # print("frame => frame", total_nb_frames - 1 - (nb_keyframe_src + nb_keyframe_dst + nb_kf_kf_connexions))

        graph_nz_count = N_samples * N_samples_dest * (total_nb_frames - 1 - (nb_keyframe_src + nb_keyframe_dst + nb_kf_kf_connexions)) \
                        + nb_keyframe_src * N_samples_dest + nb_keyframe_dst * N_samples \
                        + nb_kf_kf_connexions

        # Source and sink links
        for t in [first_frame_idx, last_frame_idx]:
            if t in keyframe_times:
                graph_nz_count += 1
            else:
                graph_nz_count += N_samples

        graph_matrix_data = np.empty(graph_nz_count)
        graph_matrix_row = np.empty(graph_nz_count, dtype=int)
        graph_matrix_col = np.empty(graph_nz_count, dtype=int)

        # for every frame
        # - find best matching image pixels (compared to keyframe pixels)
        # - read data (3D pos, image fetures) and compute edge weights
        for t in range(first_frame_idx, last_frame_idx + 1):
            # print("Frame", t)
            # is this frame keyframed?
            if t in keyframe_times:
                kf = keyframe_by_time[t]

                # kf_pos_maps = (np.round(kf["pos_2d"] * maps_res)).astype(int)
                kf_pos_feats = (np.round(kf["pos_2d"] * np.array([res_x, res_y]))).astype(int)

                pixels_t = kf_pos_feats.reshape((1, 2))
                pixels_t_3d = pos_3d_archive[(np.repeat(t, 1), index_into_data(kf["pos_2d"].reshape((1, 2)), (1, 1), maps_res))]
                # flow_curr_to_next = flow_3d_archive[(np.repeat(t, 1), index_into_data(kf["pos_2d"].reshape((1, 2)), (1, 1), maps_res))]

                # We do not trust the flow coming from a keyframed pixel, since it might be lying on an unsafe region
                # This flow value is only used for the proximity metric in the edge weights,
                # this means that at the frame (k+1) right after a keyframe at (k), we directly compare positions V_{k+1} with V_k
                flow_curr_to_next = np.zeros((pixels_t_3d.shape))

                kf_match_cost = np.zeros((1, 1))


            else:
                # s = time.time()

                feature_mask = masks[t]

                # print("time computing mask", time.time() - s)

                # Flat kf feature match cost for this frame
                kf_match_cost = match_best_kf_feature_cost[t]

                # Apply mask: put a super high cost on pixels that are unreliable
                kf_match_cost[~feature_mask] = max_feature_cost

                # Sort
                sorted_pixel_idx = np.argsort(kf_match_cost)
                to_keep_idx, to_prune_idx = np.split(sorted_pixel_idx, [N_samples])
                keep_indices = np.zeros(len(sorted_pixel_idx), dtype=bool)
                keep_indices[to_keep_idx] = True

                kf_match_cost = kf_match_cost[to_keep_idx]

                # Read nodes 3D/flow data
                pixels_y_t, pixels_x_t = np.unravel_index(np.arange(res_x * res_y, dtype=int)[to_keep_idx], (res_y, res_x), order='F')
                pixels_t = np.column_stack([pixels_x_t, pixels_y_t])

                pixels_t_3d = pos_3d_archive[(np.repeat(t, len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), maps_res))]
                flow_curr_to_next = flow_3d_archive[(np.repeat(t, len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), maps_res))]

            nodes_2d_positions = np.row_stack([nodes_2d_positions, pixels_t])

            # Image features
            if feature_similarity_weight > 0:
                pixels_t_features = all_frames_features[t, index_into_data(pixels_t, (res_x, res_y), (res_x, res_y))]
            else:
                pixels_t_features = None

            nodes_indices_t = current_node_idx + np.arange(len(pixels_t))

            # Compute edge weights with nodes from prev frame
            if t > first_frame_idx:
                s = time.time()

                prev_pos_3d = prev_frame_nodes_data["pos_3d"]
                prev_features = prev_frame_nodes_data["features"]
                prev_indices = prev_frame_nodes_data["indices"]


                current_nz_data_idx = compute_all_edge_weights(
                    prev_pos_3d, prev_features, prev_indices, flow_prev_to_curr,
                    pixels_t_3d, pixels_t_features, nodes_indices_t, kf_match_cost,
                    proximity_weight, feature_similarity_weight, targets_feature_similarity_weight, 
                    graph_matrix_data, graph_matrix_row, graph_matrix_col, 
                    current_nz_data_idx)

                # print("time computing edge weights", time.time() - s)

            prev_frame_nodes_data = {"pos_3d": pixels_t_3d, "features": pixels_t_features, "indices": nodes_indices_t, "features_to_kf": kf_match_cost}
            current_node_idx += len(nodes_indices_t)

            flow_prev_to_curr = flow_curr_to_next

            # Set source/sink for first/last frames
            if t == first_frame_idx:
                source_dst_indices = prev_frame_nodes_data["indices"]
            if t == last_frame_idx:
                sink_src_indices = prev_frame_nodes_data["indices"]


        print(f"Time to compute all edge weights {time.time() - start_graph_weights:.2f}s")

        # Add source and sink links
        # - source
        graph_matrix_data[current_nz_data_idx:current_nz_data_idx+len(source_dst_indices)] = 1
        graph_matrix_row[current_nz_data_idx:current_nz_data_idx+len(source_dst_indices)] = source_idx
        graph_matrix_col[current_nz_data_idx:current_nz_data_idx+len(source_dst_indices)] = source_dst_indices

        current_nz_data_idx += len(source_dst_indices)

        # - sink
        graph_matrix_data[current_nz_data_idx:current_nz_data_idx+len(sink_src_indices)] = 1
        graph_matrix_row[current_nz_data_idx:current_nz_data_idx+len(sink_src_indices)] = sink_src_indices
        graph_matrix_col[current_nz_data_idx:current_nz_data_idx+len(sink_src_indices)] = sink_idx

        current_nz_data_idx += len(sink_src_indices)

        if (np.any(graph_matrix_data < 0)):
            print(f"WARNING: some graph weights are < 0! min value = {np.min(graph_matrix_data)}. Clipping to zero to prevent failure in graph shortest path solve.")
            graph_matrix_data = np.clip(graph_matrix_data, a_min=0, a_max=None)

        start_graph_build = time.time()
        graph_csr = csr_matrix((graph_matrix_data, (graph_matrix_row, graph_matrix_col)), shape=(graph_dim,graph_dim))
        print(f"Time creating graph matrix: {time.time() - start_graph_build:.2f}s")

        # Find the shortest path from source to sink
        start = time.time()
        dist_matrix, predecessors = shortest_path(csgraph=graph_csr, directed=True, indices=source_idx, return_predecessors=True)
        print(f"Time finding the shortest path: {time.time() - start:.2f}s")

        print("Full path cost", dist_matrix[sink_idx])

        # Find all nodes in the shortest path
        current_node = sink_idx
        shortest_path_nodes_idx = []
        success = True
        while True:
            # print("Current node", current_node, "Distance to start", dist_matrix[current_node])
            current_node = predecessors[current_node]
            # print("Predecessor", current_node)
            if (current_node == source_idx):
                break
            if (current_node == -9999):
                print("No path between source and sink")
                success = False
                break
            shortest_path_nodes_idx.insert(0, current_node)

        shortest_path_2d_positions = nodes_2d_positions[shortest_path_nodes_idx]

    # s = time.time()
    flat_shortest_path_indices = index_into_data(shortest_path_2d_positions, (res_x, res_y), maps_res)
    shortest_path_3d_velocities = flow_3d_archive[(np.arange(first_frame_idx, last_frame_idx+1), flat_shortest_path_indices)]
    shortest_path_3d_positions = pos_3d_archive[(np.arange(first_frame_idx, last_frame_idx+1), flat_shortest_path_indices)]

    # For keyframes, sample the position/velocity at the higher map resolution
    for kf in keyframes:
        shortest_path_3d_positions[kf['t'] - first_frame_idx] = pos_3d_archive[(np.repeat(kf['t'], 1), index_into_data(kf["pos_2d"].reshape((1, 2)), (1, 1), maps_res))].flatten()

        shortest_path_3d_velocities[kf['t'] - first_frame_idx] = flow_3d_archive[(np.repeat(kf['t'], 1), index_into_data(kf["pos_2d"].reshape((1, 2)), (1, 1), maps_res))].flatten()
        # If scene flow is unsafe: copy velocity from prev/next non-keyframed frame
        kf_time = kf['t']
        # Check if this keyframe has at least 1 non-keyframed neighbor
        # if not, then its flow will not influence the result anyway
        if (kf_time == first_frame_idx or (kf_time - 1) in keyframe_times) and (kf_time == last_frame_idx or (kf_time + 1) in keyframe_times):
            continue
        kf_flow_is_safe = masks[kf_time, index_into_data(kf["pos_2d"].reshape((1, 2)), (1, 1), (res_x, res_y)).flatten()]
        # print(f"Keyframe {kf_time} is safe? {kf_flow_is_safe}")
        if not kf_flow_is_safe:
            # Replace velocity by temporal neighbor value
            if (kf_time == first_frame_idx or (kf_time - 1) in keyframe_times):
                replacement_idx = kf_time + 1
                shortest_path_3d_velocities[kf['t'] - first_frame_idx] = shortest_path_3d_velocities[replacement_idx - first_frame_idx]
            elif (kf_time == last_frame_idx or (kf_time + 1) in keyframe_times):
                replacement_idx = kf_time - 1
                shortest_path_3d_velocities[kf['t'] - first_frame_idx] = shortest_path_3d_velocities[replacement_idx - first_frame_idx]
            else:
                # interpolate both neighbors
                shortest_path_3d_velocities[kf['t'] - first_frame_idx] = np.average([
                                                                            shortest_path_3d_velocities[kf['t'] - first_frame_idx - 1],
                                                                            shortest_path_3d_velocities[kf['t'] - first_frame_idx + 1]
                                                                        ], axis = 0)

    # print(f"memory end: {Process().memory_info().rss:e}")
    

    return shortest_path_3d_positions, shortest_path_3d_velocities


def optimize_trajectory(
    video_name       : str,
    keyframes        : List[dict],
    target_velocities: np.ndarray,
    initial_positions: np.ndarray,
    is_presolved     : np.ndarray
    ): 
    '''
    Recovers a stable 3D trajectory by solving the Poisson problem to best match the target velocities (found via tracking)
    and match the user keyframe positions (hard constraints).
    This corresponds to the paragraph "Recovering stable, high-resolution trajectories" of Sec. 5.2.

    Args:
        video_name (str)
        keyframes (List[dict]): list of keyframes
        target_velocities (np.ndarray): scene flow that we will aim to match with the solved trajectory
        initial_positions (np.ndarray): initial 3D positions (these are only used at presolved frames or as soft objectives at keyframes that have only a 2D position constraint)
        is_presolved (np.ndarray): array of boolean flags that indicate whether the position at each frame is presolved (eg, in the case where the user specifies they want linear interpolation instead of tracking)

    Returns:
        trajectory_pts (np.ndarray): the optimized 3D trajectory points
    '''

    # Filter out keyframes that don't contain position data or are at presolved positions
    keyframes = [kf for kf in keyframes if (not is_presolved[kf['t']] and ("pos_3d" in kf.keys() or "pos_2d" in kf.keys()))]

    # Data
    camera_data = np.load(os.path.join(backend_data_root_folder, video_name, "cameras.npz"))

    total_nb_frames, maps_res_x, maps_res_y = get_maps_dims(video_name)
    maps_res = (maps_res_x, maps_res_y)

    res_x, res_y = maps_res

    # Build linear system matrix
    A_data = []
    A_row = []
    A_col = []

    N = len(initial_positions)

    b = np.zeros((N, 3))

    # SOFT VELOCITY CSTR => velocity should match 3D flow vectors
    # Case i = 1
    # if 0 not in keyframe_times:
    sparse_add_value(1, 0, 0, A_data, A_row, A_col, flat=True)
    sparse_add_value(-1, 0, 1, A_data, A_row, A_col, flat=True)

    b[0, :] += -target_velocities[0, :]

    for i in range(1, N-1):
        # nb_soft_cstr = 0
        # if i not in keyframe_times:
        b[i, :] += -target_velocities[i, :]
        sparse_add_value(-1, i, i+1, A_data, A_row, A_col, flat=True)
            # nb_soft_cstr += 1 

        # if (i-1) not in keyframe_times:
        sparse_add_value(-1, i, i-1, A_data, A_row, A_col, flat=True)
        b[i, :] += target_velocities[i-1, :]
            # nb_soft_cstr += 1 

        # if nb_soft_cstr > 0:
        sparse_add_value(2, i, i, A_data, A_row, A_col, flat=True)
        

    # Case i = N-1
    # if (N-2) not in keyframe_times:
    sparse_add_value(-1, N-1, N-2, A_data, A_row, A_col, flat=True)
    sparse_add_value(1, N-1, N-1, A_data, A_row, A_col, flat=True)

    b[N-1, :] += target_velocities[N-2, :]

    b_flat = b.flatten()

    system_current_nb_rows = 3 * N

    # Add rows for keyframe ray parameter variables
    # if keyframe is defined as a 2D position only (ie, ray parameter is a variable)
    system_row_index_per_keyframe = []
    for kf in keyframes:

        if "pos_3d" not in kf.keys():
            kf_frame = kf["t"]
            kf_pos = kf["pos_2d"]
            next_frame = kf_frame + 1
            prev_frame = kf_frame - 1
            kf_row_index = system_current_nb_rows
            system_row_index_per_keyframe.append(kf_row_index)
            system_current_nb_rows += 1

            kf_ray_origin, kf_ray_dir = get_camera_ray(kf_pos, kf_frame, camera_data)

            b_kf = 0

            if kf_frame < N-1:
                # print("low")
                # derivative wrt keyframe
                sparse_add_value(
                    kf_ray_dir.T @ kf_ray_dir, 
                    kf_row_index,
                    kf_row_index,
                    A_data, A_row, A_col,
                    flat=False
                )
                for i in range(3):
                    sparse_add_value(
                        -kf_ray_dir[i], 
                        kf_row_index,
                        3 * next_frame + i,
                        A_data, A_row, A_col,
                        flat=False
                    )
                b_kf += -kf_ray_origin.T @ kf_ray_dir - target_velocities[kf_frame, :].T @ kf_ray_dir

            if kf_frame > 0:
                # print("high")

                sparse_add_value(
                    kf_ray_dir.T @ kf_ray_dir, 
                    kf_row_index,
                    kf_row_index,
                    A_data, A_row, A_col,
                    flat=False
                )
                for i in range(3):
                    sparse_add_value(
                        -kf_ray_dir[i], 
                        kf_row_index,
                        3 * prev_frame + i,
                        A_data, A_row, A_col,
                        flat=False
                    )
            
                b_kf += -kf_ray_origin.T @ kf_ray_dir + target_velocities[prev_frame, :].T @ kf_ray_dir

            b_flat = np.append(b_flat, b_kf)
        else:
            system_row_index_per_keyframe.append(-1)

        

    A = csr_matrix((A_data, (A_row, A_col)), shape=(system_current_nb_rows, system_current_nb_rows), dtype=float)

    # Add hard constraints (lagrange multipliers method)
    C_data = []
    C_row = []
    C_col = []

    hard_cstr_row_idx = 0
    for kf, kf_row_index in zip(keyframes, system_row_index_per_keyframe):
        kf_frame = kf["t"]
        # Case where the keyframe is a 2D position: add ray constraint
        # pos_3d = ray_origin + ray_dir * ray_param
        if "pos_3d" not in kf.keys():
            if "pos_2d" not in kf.keys():
                continue
            kf_pos = kf["pos_2d"]

            sparse_add_value(-1.0, hard_cstr_row_idx, kf_frame, C_data, C_row, C_col, flat=True)
            kf_ray_origin, kf_ray_dir = get_camera_ray(kf_pos, kf_frame, camera_data)

            for i in range(3):
                sparse_add_value(kf_ray_dir[i], 3 * hard_cstr_row_idx + i, kf_row_index, C_data, C_row, C_col, flat=False)
            b_flat = np.append(b_flat, -kf_ray_origin)
        # Case where the keyframe is a 3D position: add hard match constraint
        else:
            # Add hard 3D constraint
            kf_pt = kf["pos_3d"]
            sparse_add_value(1.0, hard_cstr_row_idx, kf_frame, C_data, C_row, C_col, flat=True)
            b_flat = np.append(b_flat, kf_pt)
        hard_cstr_row_idx += 1
    
    # Presolved positions
    presolved_indices = np.flatnonzero(is_presolved)
    for idx in presolved_indices:
        # Add hard 3D constraint
        init_pt = initial_positions[idx]
        sparse_add_value(1.0, hard_cstr_row_idx, idx, C_data, C_row, C_col, flat=True)
        b_flat = np.append(b_flat, init_pt)
        hard_cstr_row_idx += 1


    C = csr_matrix((C_data, (C_row, C_col)), shape=(3*(len(keyframes) + len(presolved_indices)), system_current_nb_rows), dtype=float)

    # print(C.todense())

    # Second soft cstr: 3D end points should be close to the corresponding positions of graph nodes on shortest path
    A_prox_data = []
    A_prox_row = []
    A_prox_col = []

    b_prox = np.zeros(len(b_flat))
    for kf, kf_row_index in zip(keyframes, system_row_index_per_keyframe):
        if "pos_3d" not in kf.keys():
            kf_frame = kf["t"]
            # kf_pos = (kf["pos_2d"] * np.array([res_x, res_y])).astype(int)
            kf_pos = kf["pos_2d"]

            sparse_add_value(1.0, kf_frame, kf_frame, A_prox_data, A_prox_row, A_prox_col, flat=True)
            b_prox[[3 * kf_frame + 0, 3 * kf_frame + 1, 3 * kf_frame + 2]] += initial_positions[kf_frame]

            kf_ray_origin, kf_ray_dir = get_camera_ray(kf_pos, kf_frame, camera_data)

            sparse_add_value(
                kf_ray_dir.T @ kf_ray_dir, 
                kf_row_index,
                kf_row_index,
                A_prox_data, A_prox_row, A_prox_col,
                flat=False
            )
            b_prox[kf_row_index] += initial_positions[kf_frame].T @ kf_ray_dir - kf_ray_origin.T @ kf_ray_dir

    A_prox = csr_matrix((A_prox_data, (A_prox_row, A_prox_col)), shape=(system_current_nb_rows, system_current_nb_rows), dtype=float)

    prox_weight = 0.01

    M = bmat([[A + prox_weight * A_prox, C.T], [C, None]],format = 'csr')

    # Solve linear system
    X = spsolve(M, b_flat + prox_weight * b_prox)

    # Extract result: 3D trajectory points
    pts = X[:3*N].reshape((N, 3))

    # kf_ray_params = []
    # for kf, kf_row_index in zip(keyframes, system_row_index_per_keyframe):
    #     kf_ray_params.append(X[kf_row_index])


    return pts