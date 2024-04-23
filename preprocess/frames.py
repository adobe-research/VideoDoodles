import os
import numpy as np
import cv2

from videodepth_video import VideoData


def prepare_frames(video : VideoData, ui_data_path : str):

    # Create temp frame folders
    color_out_temp_folder = os.path.join(ui_data_path, video.video_name, "color")
    if not os.path.exists(color_out_temp_folder):
        os.makedirs(color_out_temp_folder)

    # We resize videos to match depth resolution
    width, height = video.get_depth_res()

    for fid in range(video.first_frame_idx, video.last_frame_idx + 1):
        frame = video.get_frame(fid, resize_res=(width, height))

        # Export color frame
        frame_name = f"{fid - video.first_frame_idx:04d}.png"    
        cv2.imwrite(os.path.join(color_out_temp_folder, frame_name), frame)

    # Ffmpeg videos and delete temp folders
    # - this ffmpeg command makes sure that the video is encoded such that it can be scrubbed frame by frame in the web viewer
    cmd = f"ffmpeg -y -framerate 25 -i {color_out_temp_folder}/%04d.png -c:v libx264 -x264-params keyint=1:scenecut=0 -pix_fmt yuv420p {os.path.join(ui_data_path, video.video_name)}/vid.mp4"
    os.system(cmd)
    os.system(f"rm -rf {color_out_temp_folder}")