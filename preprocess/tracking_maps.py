import numpy as np
import cv2
import os

from videodepth_video import VideoData


# From a VideoData object, create the memmaps that we use in the tracking code
# - 3D scene flow
# - 3D point clouds


def prepare_tracking_maps(
        video            : VideoData,
        backend_data_path: str
    ):
    
    # We will create all maps at the flow resolution to avoid interpolating flow vectors
    maps_width, maps_height = video.get_flow_res()
    total_nb_frames = video.get_frame_count()

    all_flows = np.empty((total_nb_frames, maps_height * maps_width, 3))
    all_positions = np.empty((total_nb_frames, maps_height * maps_width, 3))

    for t in range(video.first_frame_idx, video.last_frame_idx + 1):
        Vs = video.get_point_cloud(t, resize_res=(maps_width, maps_height))
        flow_3d = video.get_flow_3d(t if t < video.last_frame_idx else t - 1)
        all_flows[t - video.first_frame_idx] = flow_3d
        all_positions[t - video.first_frame_idx] = Vs

    if not os.path.exists(os.path.join(backend_data_path, video.video_name)):
        os.makedirs(os.path.join(backend_data_path, video.video_name))

    # np.savez(
    #     os.path.join(backend_data_folder, video_name, "maps_3d.npz"), 
    #     flows=all_flows,
    #     positions=all_positions,
    #     dimensions=(total_nb_frames, res_x, res_y))

    np.save(
        os.path.join(backend_data_path, video.video_name, "maps_dim.npy"),
        np.array([total_nb_frames, maps_width, maps_height], dtype=np.uint64)
    )

    flow_memmap = np.memmap(
        os.path.join(backend_data_path, video.video_name, "flow.memmap"), 
        dtype=all_flows.dtype,
        mode="w+",
        shape=all_flows.shape
    )
    flow_memmap[:] = all_flows[:]
    flow_memmap.flush()
    # print(all_flows.shape)

    pos_memmap = np.memmap(
        os.path.join(backend_data_path, video.video_name, "pos.memmap"), 
        dtype=all_positions.dtype,
        mode="w+",
        shape=all_positions.shape
    )
    # print(all_positions.shape)
    pos_memmap[:] = all_positions[:]
    pos_memmap.flush()


