import argparse
import json
import os
import time
from pathlib import Path

import numpy as np

# Library and utility scripts necessary only for debug display
try:
    import cv2
    import polyscope as ps
    ps.init()
    ps.set_up_dir("neg_y_up")
    

except ImportError:
    print("Debug display scripts are unavailable.  Run with flag -H")


from .paths import keyframe_records_folder, backend_data_root_folder, preprocessed_data_folder
from .convert import dejsonize
from .tracking_position import find_motion_path, optimize_trajectory
from .read_scene_data import (arrange_colors, get_features,
                                get_features_dims, get_flows, get_maps_dims,
                                get_positions, index_into_data)

traj_export_folder = str((Path(__file__).resolve().parent.parent / 'exports' / 'trajectory'))

# Run with something like:
# cd app/backend
# python3 -m scripts.test_optimize_trajectory --kf train_1kf


if __name__ == "__main__":


    parser = argparse.ArgumentParser()

    parser.add_argument('--kfs', type=str, default=None, required=True)
    parser.add_argument('--export', '-E', help="Export trajectory positions as a npz file.", default=False, dest="export", action="store_true")
    parser.add_argument('-H', default=True, dest="display", action="store_false")
    parser.add_argument('--proximity_weight', type=float, default=1)
    parser.add_argument('--feature_similarity_weight', type=float, default=0)
    parser.add_argument('--normal_similarity_weight', type=float, default=0)
    parser.add_argument('--targets_global_similarity_weight', type=float, default=0)

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
    print(keyframes)

    # Graph search
    start = time.time()
    initial_positions, soft_velocity_cstr = find_motion_path(
        vid, keyframes, 
        proximity_weight=args.proximity_weight,
        feature_similarity_weight=args.feature_similarity_weight,
        targets_feature_similarity_weight=args.targets_global_similarity_weight)

    print(f"Total graph step time {time.time() - start}")

    # Poisson step
    poisson_start = time.time()
    is_presolved = np.zeros(len(soft_velocity_cstr), dtype=bool)
    pts_opt = optimize_trajectory(
        vid, 
        keyframes, 
        soft_velocity_cstr, 
        initial_positions, 
        is_presolved
    )

    print(f"Total poisson step time {time.time() - poisson_start}")
    print(f"Total time traj {time.time() - start}")

    # Store data needed for orientation step too
    velocity_scale = np.quantile(np.linalg.norm(soft_velocity_cstr, axis = 1), 0.9)
    if velocity_scale < 1e-4:
        matching_weights = np.zeros(len(soft_velocity_cstr))
    else:
        matching_weights = np.clip(np.linalg.norm(soft_velocity_cstr, axis = 1) / velocity_scale, 0, 1)

    if args.display:
        ps.init()
        ps.set_up_dir("neg_y_up")
        ps.remove_all_structures()
        # Get all frames data
        frame_archive = np.load(os.path.join(preprocessed_data_folder, vid, "frames.npz"))
        total_nb_frames, res_x, res_y = get_maps_dims(vid)
        pos_3d_archive = get_positions(vid, total_nb_frames, (res_x, res_y))


        for kf in keyframes:
            im = cv2.resize(frame_archive[f"frame_{kf['t']:05d}"].astype(np.float32), (res_x, res_y))

            pixels_y_t, pixels_x_t = np.unravel_index(np.arange(res_x * res_y, dtype=int), (res_y, res_x), order='F')
            pixels_t = np.column_stack([pixels_x_t, pixels_y_t])
            Vs = pos_3d_archive[(np.repeat(kf['t'], len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), (res_x, res_y)))]
            all_colors_flat = arrange_colors(im)

            ps_im = ps.register_point_cloud(f"pts at keyframe t={kf['t']}", Vs, point_render_mode='quad', radius=0.001, enabled=False)
            ps_im.add_color_quantity("colors", all_colors_flat / 255, enabled=True)

        ps.register_point_cloud("solved pts", pts_opt)
        ps_pts = ps.register_point_cloud("initial pts", initial_positions)
        ps_pts.add_vector_quantity("scene flow", soft_velocity_cstr)

        ps.show()

    # Export
    if args.export:
        np.savez(os.path.join(traj_export_folder, f"{args.kfs}.npz"),
            ours=pts_opt,
            no_poisson=initial_positions,
            vid=vid,
            kfs_file_name=args.kfs,
            target_velocity=soft_velocity_cstr,
            target_matching_weights=matching_weights
        )
