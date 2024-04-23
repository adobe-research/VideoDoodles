import argparse
import numpy as np
from pathlib import Path

# Library and utility scripts necessary only for debug display
try:
    import polyscope as ps
except ImportError:
    print("Debug display scripts are unavailable.  Run with flag -E to export data without viewing it.")

from videodepth_video import VideoData
from cameras import prepare_cameras
from depth_maps import prepare_depth_maps
from frames import prepare_frames
from videowalk_features import prepare_features
from tracking_maps import prepare_tracking_maps
from tracking_masks import prepare_masks

from default_paths import default_backend_data_folder, default_frontend_data_folder, data_root_folder


def prepare_all(
    video_name       : str,
    raw_data_path    : str,
    ui_data_path     : str,
    backend_data_path: str,
    first_frame_idx  : int = 0,
    last_frame_idx   : int = None,
    only_do_step     : int = None,
    ): 

    try:
        video_data = VideoData(Path(raw_data_path), video_name, first_frame_idx, last_frame_idx)
    except FileExistsError:
        print(f"Aborting preprocess for {video_name}.")
        return

    print(f"Preparing all data for video {video_name}...")

    if only_do_step is None or only_do_step == 1:
        print(f"- (1/6) Preparing frames for {video_name}")
        prepare_frames(video_data, ui_data_path)

    if only_do_step is None or only_do_step == 2:
        print(f"- (2/6) Preparing cameras for {video_name}")
        prepare_cameras(video_data, ui_data_path, backend_data_path)

    if only_do_step is None or only_do_step == 3:
        print(f"- (3/6) Preparing depth for {video_name}")
        prepare_depth_maps(video_data, ui_data_path)

    if only_do_step is None or only_do_step == 4:
        print(f"- (4/6) Preparing deep image feature maps for {video_name}")
        feat_width, feat_height = prepare_features(video_data, backend_data_path)

    if only_do_step is None or only_do_step == 5:
        print(f"- (5/6) Preparing 3D maps (positions+flows) for {video_name}")
        prepare_tracking_maps(video_data, backend_data_path)

    if only_do_step is None or only_do_step == 6:
        print(f"- (6/6) Preparing binary masks to indicate pixels with untrustworthy 3D flow for {video_name}")
        prepare_masks(video_data, backend_data_path, (feat_width, feat_height))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--vid', type=str, default=None, required=True)
    parser.add_argument('--raw-data-path', type=str, default=data_root_folder, required=False, help="path to the folder public/data/ in the web UI repo")
    parser.add_argument('--ui-data-path', type=str, default=default_frontend_data_folder, required=False, help="path to the folder public/data/ in the web UI repo")
    parser.add_argument('--backend-data-path', type=str, default=default_backend_data_folder, required=False, help="path to the folder to store backend data")
    parser.add_argument("--export", "-E", default=False, dest='export', action="store_true")
    parser.add_argument("--last-frame-idx", default=None, type=int)
    parser.add_argument("--first-frame-idx", default=0, type=int)
    parser.add_argument("--only-step", default=None, type=int)

    args = parser.parse_args()

    if args.export:
        prepare_all(args.vid, args.raw_data_path, args.ui_data_path, args.backend_data_path, args.first_frame_idx, args.last_frame_idx, args.only_step)
    else:
        print("Viewing debug visualisations")
        ps.init()
        ps.set_up_dir("neg_y_up")

        video_data = VideoData(Path(args.raw_data_path), args.vid)

        flow_width, flow_height = video_data.get_flow_res()

        cameras = np.empty((0, 3))
        forwards = np.empty((0, 3))

        for t in range(video_data.first_frame_idx, video_data.last_frame_idx + 1, 5):
            print(f"Frame {t}")
            Vs = video_data.get_point_cloud(t, resize_res=(flow_width, flow_height))
            flow_3d = video_data.get_flow_3d(t if t < video_data.last_frame_idx else t - 1)
            colors = video_data.get_pixel_wise_color(t, (flow_width, flow_height))

            ps_pts = ps.register_point_cloud("frame", Vs, point_render_mode='quad')
            ps_pts.add_color_quantity("color", colors / 255, enabled=True)
            ps_pts.add_vector_quantity("flow 3d", flow_3d, vectortype="ambient")

            # Camera
            cam_pos = video_data.get_camera(t).get_position()
            cam_forward = video_data.get_camera(t).get_forward()

            cameras = np.row_stack([cameras, cam_pos])
            forwards = np.row_stack([forwards, cam_forward])

            ps_cams = ps.register_point_cloud("cameras", cameras)
            ps_cams.add_vector_quantity("forward", forwards, vectortype="standard", enabled=True)

            ps.show()

