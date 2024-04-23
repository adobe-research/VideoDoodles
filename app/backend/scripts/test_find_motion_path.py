import argparse
import json
import os
import time
import numpy as np

# Library and utility scripts necessary only for debug display
try:
    import cv2
    import polyscope as ps
    ps.init()
    ps.set_up_dir("neg_y_up")

except ImportError:
    print("Debug display scripts are unavailable. Run with flag -H")


from .paths import keyframe_records_folder, preprocessed_data_folder
from .convert import dejsonize
from .tracking_position import find_motion_path
from .paths import backend_data_root_folder
from .read_scene_data import (arrange_colors, get_features,
                                get_features_dims, get_flows, get_maps_dims,
                                get_positions, index_into_data)

# Run with something like:
# cd app/backend
# python3 -m scripts.test_find_motion_path --kf train_1kf
    

if __name__ == "__main__":


    parser = argparse.ArgumentParser()

    parser.add_argument('--kfs', type=str, default=None, required=True)
    parser.add_argument('--hide', '-H', default=True, dest="display", action="store_false")
    parser.add_argument('--proximity_weight', type=float, default=1)
    parser.add_argument('--feature_similarity_weight', type=float, default=0)
    parser.add_argument('--normal_similarity_weight', type=float, default=0)
    parser.add_argument('--targets_global_similarity_weight', type=float, default=0)
    # parser.add_argument('--prune', type=float, default=0.9)
    parser.add_argument('--perf-test', default=False, dest="perf_test", action="store_true")

    args, unknown_args = parser.parse_known_args()


    kf_records_file = os.path.join(keyframe_records_folder, args.kfs + ".json")

    if not os.path.isfile(kf_records_file):
        print(f"ERROR: file {kf_records_file} does not exist")
        exit


    with open(kf_records_file, 'r') as f:
        keyframes_data = json.load(f)

    # Load files
    vid = keyframes_data['clip']
    keyframes = dejsonize(keyframes_data['position_keyframes'])
    print("keyframes:", keyframes)

    if args.perf_test:
        # Run this 10 times and average the runtime
        start = time.time()
        print("START PERFORMANCE TEST")
        for i in range(10):
            start_i = time.time()
            print(f"START RUN {i}")
            shortest_path_3d_positions, shortest_path_3d_velocities = find_motion_path(
                vid, keyframes, 
                proximity_weight=args.proximity_weight,
                feature_similarity_weight=args.feature_similarity_weight,
                targets_feature_similarity_weight=args.targets_global_similarity_weight)
            print(f"END RUN {i} = {time.time() - start_i:.2f} s")
            print("===================")

        total_time = time.time() - start
        print(f"Runtime (avg on 10 runs) {total_time / 10:.2f}s")

    else:
        shortest_path_3d_positions, shortest_path_3d_velocities = find_motion_path(
            vid, keyframes, 
            proximity_weight=args.proximity_weight,
            feature_similarity_weight=args.feature_similarity_weight,
            targets_feature_similarity_weight=args.targets_global_similarity_weight)
        
        # Result visualisation
        if args.display:
            ps.init()
            ps.set_up_dir("neg_y_up")
            ps.remove_all_structures()
            display_frame_stride = 5
            ps_path = ps.register_point_cloud("pts in path", shortest_path_3d_positions)
            ps_path.add_vector_quantity("flow", shortest_path_3d_velocities, vectortype="ambient")

            # Get all frames data
            frame_archive = np.load(os.path.join(preprocessed_data_folder, vid, "frames.npz"))
            total_nb_frames, maps_res_x, maps_res_y = get_maps_dims(vid)
            maps_res = (maps_res_x, maps_res_y)
            T, res_x, res_y, d_feat = get_features_dims(vid)
            masks_archive = np.load(os.path.join(backend_data_root_folder, vid, "masks.npz"))
            masks = masks_archive["masks"]
            flow_3d_archive = get_flows(vid, total_nb_frames, maps_res)
            pos_3d_archive = get_positions(vid, total_nb_frames, maps_res)

            for t in range(0, len(shortest_path_3d_positions), display_frame_stride):
                print("Frame", t)

                frame = frame_archive[f"frame_{t:05d}"]
                frame = cv2.resize(frame, (res_x, res_y), interpolation=cv2.INTER_AREA)

                pixels_y_t, pixels_x_t = np.unravel_index(np.arange(res_x * res_y, dtype=int), (res_y, res_x), order='F')
                pixels_t = np.column_stack([pixels_x_t, pixels_y_t])
                Vs = pos_3d_archive[(np.repeat(t, len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), maps_res))]
                all_colors_flat = arrange_colors(frame)

                mask_t = masks[t]

                flows_t = flow_3d_archive[(np.repeat(t, len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), maps_res))]

                # Filter out super far away pts for display (uncomment if encountering display issues caused by outlier points)
                # avg_pos = np.mean(Vs, axis=0)
                # dist_to_avg = np.linalg.norm(Vs - avg_pos, axis=1)
                # max_dist = np.nanquantile(dist_to_avg, 0.99)
                # too_far_away_pixels = dist_to_avg > max_dist
                # print(f"For display: filtered out {np.count_nonzero(too_far_away_pixels)} pixels (too far away from center)")
                # Vs = Vs[~too_far_away_pixels]
                # all_colors_flat = all_colors_flat[~too_far_away_pixels]
                # mask_t = mask_t[~too_far_away_pixels]
                # flows_t = flows_t[~too_far_away_pixels]

                ps_pts = ps.register_point_cloud(f"pts", Vs, point_render_mode='quad')
                ps_pts.add_color_quantity("colors", all_colors_flat / 255, enabled=True)

                ps_pts.add_vector_quantity("flows", flows_t, vectortype="ambient")

                ps_pts.add_scalar_quantity("safe?", mask_t)


                # keyframes
                for kf in keyframes:
                    kf_pos = (np.round(kf["pos_2d"] * np.array([res_x, res_y]))).astype(int)

                    pixels_t = kf_pos.reshape((1, 2))
                    pixels_t_3d = pos_3d_archive[(np.repeat(kf['t'], len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), maps_res))]
                    pixels_t_3d_2 = pos_3d_archive[(np.repeat(kf['t'], 1), index_into_data(kf["pos_2d"].reshape((1, 2)), (1, 1), maps_res))]

                    ps.register_point_cloud(f"keyframe {kf['t']}", pixels_t_3d)
                    ps.register_point_cloud(f"keyframe (new) {kf['t']}", pixels_t_3d_2)


                ps.show()