import numpy as np
import os
from typing import List, Tuple
from pathlib import Path
import cv2

from videodepth_camera import Camera

frames_file_name            = "frames.npz"
disparities_file_name       = "resized_disps.npz"
cameras_file_name           = "refined_cameras.txt"
flows_file_name             = "flows.npz"
flows_consistency_file_name = "flows_con.npz"

class VideoData: 
    video_name      : str
    root_folder_path: Path
    first_frame_idx : int
    last_frame_idx  : int

    cameras : List[Camera]

    down_scale_factor: float
    camera_near      : float
    camera_far       : float
    depth_range      : float
    depth_offset     : float

    def __init__(self, root_folder : Path, name : str, first_frame_idx : int = 0, last_frame_idx : int = None) -> None:
        self.video_name = name
        self.root_folder_path = root_folder
        self.first_frame_idx = first_frame_idx
        self.last_frame_idx = last_frame_idx
        if last_frame_idx is None:
            self.last_frame_idx = self.get_total_frame_count() - 1

        if not self.video_is_valid():
            raise FileExistsError(f"Video {name} cannot be preprocessed because some data files are missing.")
        
        self.preload_cameras()
        self.normalize_scene_scale()

    def root_dir(self) -> Path:
        return self.root_folder_path / self.video_name

    def video_is_valid(self) -> bool:
        '''Check if all necessary data files exist for the video to be preprocessed
        '''
        valid = True
        root_dir = self.root_dir()
        valid = valid and root_dir.is_dir()
        valid = valid and (root_dir / frames_file_name).is_file()
        valid = valid and (root_dir / disparities_file_name).is_file()
        valid = valid and (root_dir / cameras_file_name).is_file()
        valid = valid and (root_dir / flows_file_name).is_file()
        valid = valid and (root_dir / flows_consistency_file_name).is_file()

        return valid
    
    def get_total_frame_count(self) -> int:
        frames_npz_path = self.root_dir() / frames_file_name
        frame_archive = np.load(frames_npz_path)
        return len(list(filter(lambda k: "frame_" in k, frame_archive.keys())))
    
    def get_frame_count(self) -> int:
        return self.last_frame_idx - self.first_frame_idx + 1

    # Read video data
    def get_frame(self, t : int, resize_res : Tuple[int, int] = None) -> np.ndarray:
        if t < self.first_frame_idx or t > self.last_frame_idx:
            raise IndexError(f"Frame {t} is out of video bounds.")
        frames_npz_path = self.root_dir() / frames_file_name
        frame_archive = np.load(frames_npz_path)
        frame = frame_archive[f"frame_{t:05d}"]
        # Resize to working size
        if resize_res is not None:
            frame = cv2.resize(frame, resize_res, interpolation=cv2.INTER_AREA)
        return frame
    
    def get_pixel_wise_color(self, t : int, resize_res : Tuple[int, int] = None) -> np.ndarray:
        frame = self.get_frame(t, resize_res)
        height, width, _ = frame.shape
        # flatten
        colors = np.transpose(frame, (1, 0, 2))
        colors = colors.reshape((width*height, 3))
        # BGR to RGB (reverse color channels)
        colors = colors[:, ::-1]
        return colors
    
    def get_raw_disparity(self, t : int) -> np.ndarray:
        if t < self.first_frame_idx or t > self.last_frame_idx:
            raise IndexError(f"Frame {t} is out of video bounds.")
        disparity_npz_path = self.root_dir() / disparities_file_name
        disp_archive = np.load(disparity_npz_path)
        return disp_archive[f"disp_{t:05d}"]

    def get_camera(self, t : int) -> Camera:
        if t < self.first_frame_idx or t > self.last_frame_idx:
            raise IndexError(f"Frame {t} is out of video bounds.")
        return self.cameras[t]
    
    def get_depth_map(self, t : int, resize_res : Tuple = None) -> np.ndarray:
        disp = self.get_raw_disparity(t)
        disparity = self.get_camera(t).scale * disp + self.get_camera(t).shift
        disparity[disparity < 1e-6] = 1e-6
        depth_map = np.squeeze(1.0/disparity)

        if resize_res is not None:
            depth_map = cv2.resize(depth_map, resize_res, interpolation=cv2.INTER_AREA)

        return depth_map
    
    def get_depth_res(self) -> Tuple[int, int]:
        disp = self.get_raw_disparity(0)
        height, width, _ = disp.shape
        return width, height


    def get_flow(self, t : int) -> np.ndarray:
        if t < self.first_frame_idx or t >= self.last_frame_idx:
            raise IndexError(f"Frame {t} is out of video bounds.")
        flow_npz_path = self.root_dir() / flows_file_name
        flow_archive = np.load(flow_npz_path)
        return flow_archive[f"flow_{t:05d}_to_{t+1:05d}"]
    
    def get_flow_res(self) -> Tuple[int, int]:
        flow = self.get_flow(0)
        height, width, _ = flow.shape
        return width, height
    
    def get_flow_consistency(self, t : int, resize_res : Tuple = None) -> np.ndarray:
        if t < self.first_frame_idx or t >= self.last_frame_idx:
            raise IndexError(f"Frame {t} is out of video bounds.")
        flow_cons_npz_path = self.root_dir() / flows_consistency_file_name
        flow_cons_archive = np.load(flow_cons_npz_path)
        flow_cons = flow_cons_archive[f"consistency_{t:05d}_{t+1:05d}"]
        if resize_res is not None:
            flow_cons = cv2.resize(flow_cons, resize_res, interpolation=cv2.INTER_AREA)
        return flow_cons
    
    def get_point_cloud(self, t : int, resize_res : Tuple[int, int] = None) -> np.ndarray:
        if resize_res is not None:
            width, height = resize_res
        else:
            # Get default width/height
            width, height = self.get_depth_res()

        ys = np.tile(np.arange(height), width)
        xs = np.repeat(np.arange(width), height)
        zs = self.get_depth_map(t, resize_res=resize_res).T.flatten()

        Vs = self.get_camera(t).unproject_to_world_space(xs, ys, zs, width, height)

        return Vs
    
    def unproject(self, t : int, xys : np.ndarray, depth_resize_res : Tuple[int, int] = None) -> np.ndarray :
        '''Unproject pixels to world space at frame t

        Args:
            t (int): frame index
            xys (np.ndarray): an array of integers containing pixel coordinates, each row is one pixel (y, x). Origin at top-left pixel. Pixel coordinates are expected to match depth map resolution (eg, go from (0, 0) to (height, width)) or the resolution specified in depth_resize_res.
            depth_resize_res (Tuple[int, int]): optional parameter to specify a new resolution for the depth maps. We expect the pixel coordinates to match this resolution. Defaults to None (depth map original resolution is used).
        Returns:
            np.ndarray: _description_
        '''
        if depth_resize_res is not None:
            width, height = depth_resize_res
        else:
            # Get default width/height
            width, height = self.get_depth_res()

        xs = xys[:, 0]
        ys = xys[:, 1]
        zs = self.get_depth_map(t, resize_res=depth_resize_res)[ys, xs]

        Vs = self.get_camera(t).unproject_to_world_space(xs, ys, zs, width, height)

        return Vs
    
    def get_flow_3d(self, t : int):
        width, height = self.get_flow_res()

        ys = np.tile(np.arange(height), width)
        xs = np.repeat(np.arange(width), height)
        pixels_a = np.column_stack([xs, ys])

        flow_ab = self.get_flow(t)

        dest_pixels_b = pixels_a + np.transpose(flow_ab, (1, 0, 2)).reshape((-1, 2)) # Pixels_a (and Vs_a) are listed in column-first order

        # sample depth map at destination pixels in frame b
        rounded_pixels_b = np.round(dest_pixels_b).astype(int)
        rounded_pixels_b[:, 0] = np.clip(rounded_pixels_b[:, 0], 0, width - 1)
        rounded_pixels_b[:, 1] = np.clip(rounded_pixels_b[:, 1], 0, height - 1)


        Vs_b = self.unproject(t + 1, rounded_pixels_b, depth_resize_res=(width, height))
        Vs_a = self.unproject(t, pixels_a, depth_resize_res=(width, height))

        return Vs_b - Vs_a

    def normalize_scene_scale(self, target_scale : int = 10, max_depth_quantile : float = 0.8) -> None:
        '''Choose scale factor and depth constants in order to make the scene fit in 'target_scale' units when rendered, and to make it possible to encode depth maps in [0, 1]

        Args:
            target_scale (int, optional): Desired max scale of the scene. Defaults to 10.
            max_depth_quantile (float, optional): This serves to cull extreme depth values (eg, an unbounded scene that goes off to infinite depth). Defaults to 0.8.
        '''
        # First compute the depth range and offsets
        depth_min = 1000000
        depth_max = 0

        for fid in range(self.first_frame_idx, self.last_frame_idx + 1):
            depth = self.get_depth_map(fid)
            # print(f"Range = {np.nanmin(depth)} - {np.nanmax(depth)}")
            depth_min = min(depth_min, np.nanmin(depth))
            depth_max = max(depth_max, np.nanquantile(depth, max_depth_quantile))

        # print(f"Overall min depth = {depth_min}, max = {depth_max}")

        depth_range = float(depth_max - depth_min)
        depth_offset = float(depth_min)

        # Choose scale factor such that scene scale ~ target_scale units (we choose target_scale = 10)
        self.down_scale_factor = depth_range / target_scale

        # Save scene scaling factors
        self.depth_range = depth_range / self.down_scale_factor
        self.depth_offset = depth_offset / self.down_scale_factor

        self.camera_near = max( 1e-3, 0.8 * depth_min / self.down_scale_factor )
        self.camera_far = depth_max / self.down_scale_factor + 1

    def preload_cameras(self) -> None:
        cameras_file = self.root_folder_path / self.video_name / cameras_file_name
        cameras = []
        with open(cameras_file, "r") as f:
            for line in f:
                line = line.strip()
                tokens = list(map(float, line.split("\t")))
                if len(tokens) == 8:
                    cameras.append(tokens)
                else:
                    focals = tokens
        cameras = np.array(cameras)
        focals = np.array(focals)
        trans = cameras[:, :3]
        rots = cameras[:, 3:6]
        scales = cameras[:, 6]
        shifts = cameras[:, 7]

        self.cameras = [None] * self.get_total_frame_count()

        for t in range(self.first_frame_idx, self.last_frame_idx + 1):
            self.cameras[t] = Camera(trans[t], rots[t], focals[0], focals[1], shifts[t], scales[t])