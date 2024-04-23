import argparse
import json
import os
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.transform import Rotation as R

from videodepth_video import VideoData


def prepare_cameras(
        video            : VideoData,
        ui_data_path     : str,
        backend_data_path: str
    ): 

    video_Ks = []
    # video_Rts = []
    video_Rs = []
    video_ts = []

    ui_cam_data = []

    width, height = video.get_depth_res()

    for i in range(video.first_frame_idx, video.last_frame_idx + 1):
        camera_i = video.get_camera(i)

        video_Ks.append(camera_i.K(width, height))
        rot_mat = camera_i.R
        translation = camera_i.t / video.down_scale_factor
        # Rt = np.column_stack([rot_mat.T, - rot_mat.T @ translation])
        # video_Rts.append(Rt)

        video_Rs.append(rot_mat)
        video_ts.append(translation)

        # Export camera data
        camera_projection_transform = camera_i.get_open_gl_projection_matrix(video.camera_near, video.camera_far, width, height)

        cam_data = {
            'rotation': R.from_matrix(rot_mat).as_quat().tolist(),
            'translation': translation.tolist(),
            'cameraProjectionTransform': camera_projection_transform.flatten().tolist(), # in threejs matrices are loaded in row-major convention
            'depthRange': video.depth_range,
            'depthOffset': video.depth_offset
        }

        ui_cam_data.append(cam_data)

    # Export cameras
    if not os.path.exists(os.path.join(ui_data_path, video.video_name)):
        os.makedirs(os.path.join(ui_data_path, video.video_name))
        
    with open(os.path.join(ui_data_path, video.video_name, 'camera.json'), 'w') as fp:
        json.dump(ui_cam_data, fp)

    # Export backend cameras file
    if not os.path.exists(os.path.join(backend_data_path, video.video_name)):
        os.makedirs(os.path.join(backend_data_path, video.video_name))


    # np.savez(os.path.join(backend_data_path, video.video_name, "gl_cameras"),
    #     Ks = np.array(video_Ks),
    #     RTs = np.array(video_Rts),
    #     res = np.array([width, height]),
    #     down_scale_factor = video.down_scale_factor,
    #     near = video.camera_near,
    #     far = video.camera_far
    # )
        
    np.savez(os.path.join(backend_data_path, video.video_name, "cameras"),
        Ks = np.array(video_Ks),
        Rs = np.array(video_Rs),
        ts = np.array(video_ts),
        res = np.array([width, height]),
        down_scale_factor = video.down_scale_factor,
        near = video.camera_near,
        far = video.camera_far
    )
