import json
import os
import argparse

import numpy as np

try:
    import polyscope as ps
    import cv2
except ImportError:
    print("Debug vis not available. Run with flag -H")

from .paths import keyframe_records_folder, traj_export_folder, orientations_export_folder, preprocessed_data_folder
from .convert import dejsonize
from .tracking_orientation import optimize_frames
from .utils import orientation_slerp
from .read_scene_data import (arrange_colors, get_features,
                                get_features_dims, get_flows, get_maps_dims,
                                get_positions, index_into_data)

# python3 -m scripts.test_orientations --traj train_orientations_1kf


if __name__ == "__main__":


    parser = argparse.ArgumentParser()

    parser.add_argument('--traj', type=str, default=None, required=True)
    parser.add_argument('--export', '-E', help="Export trajectory orientations as a npz file.", default=False, dest="export", action="store_true")
    parser.add_argument('-H', default=True, dest="display", action="store_false")
    parser.add_argument('--match-weight', type=float, default=1)
    parser.add_argument('--smooth-weight', type=float, default=10)

    args, unknown_args = parser.parse_known_args()


    traj_file = os.path.join(traj_export_folder, args.traj + ".npz")

    if not os.path.isfile(traj_file):
        print(f"ERROR: file {traj_file} does not exist")
        exit


    with open(traj_file, 'r') as f:
        traj_data = np.load(traj_file)


    kfs_file_name = str(traj_data["kfs_file_name"])
    trajectory_positions = traj_data["ours"]
    target_velocity = traj_data["target_velocity"]
    target_matching_weights = traj_data["target_matching_weights"]

    kf_records_file = os.path.join(keyframe_records_folder, kfs_file_name + ".json")

    if not os.path.isfile(kf_records_file):
        print(f"ERROR: file {kf_records_file} does not exist")
        exit

    with open(kf_records_file, 'r') as f:
        keyframes_data = json.load(f)
    vid = str(keyframes_data['clip'])
    keyframes = dejsonize(keyframes_data['orientation_keyframes'])

    # Optimize frames
    orientation_keyframes = [kf for kf in keyframes if "rot_mat" in kf.keys()]
    print(orientation_keyframes)
    kf_indices = np.array([kf['t'] for kf in orientation_keyframes])
    kf_orientations = np.array([kf['rot_mat'] for kf in orientation_keyframes])

    stride = 5

    # target_vectors = normalize(target_velocity)

    opt_orientations, segment_ids, relative_frames = optimize_frames(
        target_velocity, 
        target_matching_weights, 
        kf_indices,
        kf_orientations,
        W_match=1, W_smooth=10,
        discontinuity_threshold=0.2,
        stride=stride)

    slerp_orientations = orientation_slerp(orientation_keyframes, start_frame=0, end_frame=len(trajectory_positions) - 1)
    
    if args.display:
        ps.init()
        ps.set_up_dir("neg_y_up")

        ps.remove_all_structures()
        # Get all frames data
        frame_archive = np.load(os.path.join(preprocessed_data_folder, vid, "frames.npz"))
        total_nb_frames, res_x, res_y = get_maps_dims(vid)
        pos_3d_archive = get_positions(vid, total_nb_frames, (res_x, res_y))


        # Display keyframes
        for kf in orientation_keyframes:
            print(kf)
            kf_pos = trajectory_positions[kf['t']]
            kf_frame = kf['rot_mat']
            ps_kf = ps.register_point_cloud(f"keyframe {kf['t']}", kf_pos.reshape((1, 3)))
            for i in range(3):
                c = np.zeros(3, dtype=float)
                c[i] = 1
                c_rot = kf_frame @ c
                ps_kf.add_vector_quantity(f"axis {i} opt", c_rot.reshape((1, 3)), color=c, enabled=True)

            im = cv2.resize(frame_archive[f"frame_{kf['t']:05d}"].astype(np.float32), (res_x, res_y))

            pixels_y_t, pixels_x_t = np.unravel_index(np.arange(res_x * res_y, dtype=int), (res_y, res_x), order='F')
            pixels_t = np.column_stack([pixels_x_t, pixels_y_t])
            Vs = pos_3d_archive[(np.repeat(kf['t'], len(pixels_t)), index_into_data(pixels_t, (res_x, res_y), (res_x, res_y)))]
            all_colors_flat = arrange_colors(im)

            ps_im = ps.register_point_cloud(f"pts at keyframe t={kf['t']}", Vs, point_render_mode='quad', radius=0.001, enabled=False)
            ps_im.add_color_quantity("colors", all_colors_flat / 255, enabled=True)



        # Displays trajectory and velocity vectors
        ps_traj_line = ps.register_curve_network("trajectory line", trajectory_positions, edges='line')
        ps_traj_line.add_scalar_quantity("time", np.arange(len(trajectory_positions)), enabled=True, cmap='rainbow')
        ps_traj_in = ps.register_point_cloud("trajectory in", trajectory_positions)
        ps_traj_in.add_vector_quantity("target velocity", target_velocity)
        ps_traj_in.add_scalar_quantity("target match weight", target_matching_weights)

        # Displays orientation frames for our optimized result and the slerp solution
        ps_traj_opt = ps.register_point_cloud("frames opt", trajectory_positions)
        ps_traj_slerp = ps.register_point_cloud("frames slerp", trajectory_positions, enabled=False)

        for i in range(3):
            c = np.zeros(3, dtype=float)
            c[i] = 1
            c_opt = opt_orientations @ c
            c_slerp = slerp_orientations @ c
            ps_traj_opt.add_vector_quantity(f"axis {i} opt", c_opt, color=c, enabled=True)
            ps_traj_slerp.add_vector_quantity(f"axis {i} slerp", c_slerp, color=c, enabled=True)


        for segment_idx, base_rot in enumerate(relative_frames):
            indices_in_segment = np.flatnonzero(segment_ids == segment_idx)
            ps_segment = ps.register_point_cloud(f"segment {segment_idx}", trajectory_positions[indices_in_segment], enabled=False)

            matching_rots = opt_orientations[indices_in_segment] @ base_rot
            for i in range(3):
                c = np.zeros(3, dtype=float)
                c[i] = 1
                c_opt = matching_rots @ c
                ps_segment.add_vector_quantity(f"axis {i} opt (with base)", c_opt, color=c, enabled=True)

        ps.show()


    # Export
    if args.export:
        np.savez(os.path.join(orientations_export_folder, f"{args.kfs}.npz"),
            ours=opt_orientations,
            slerp=slerp_orientations,
            vid=vid,
            kfs_file_name=args.kfs
        )