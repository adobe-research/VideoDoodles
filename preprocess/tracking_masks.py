import numpy as np
import cv2
from typing import Tuple
from scipy import ndimage
import os

from videodepth_video import VideoData


def mask_high_depth_gradient(depth_map, threshold=0.5):
    gradx = cv2.Sobel(depth_map,cv2.CV_64F,1,0,ksize=3)
    grady = cv2.Sobel(depth_map,cv2.CV_64F,0,1,ksize=3)
    gradmag = cv2.magnitude(gradx,grady)

    # Normalize magnitude
    gradmag_normalized = (gradmag - np.min(gradmag)) / (np.max(gradmag) - np.min(gradmag))

    mask = (gradmag_normalized < threshold)

    return mask

def prepare_masks(
        video            : VideoData,
        backend_data_path: str,
        mask_res         : Tuple[int, int]
    ): 

    # We will create masks at the specified resolution (typically, we create masks at the working resolution in the tracking code, which corresponds to the feature maps resolution)
    total_nb_frames = video.get_frame_count()
    mask_res_x, mask_res_y = mask_res
    all_masks = np.empty((total_nb_frames, mask_res_x * mask_res_y), dtype=bool)

    # This is the resolution in which we compute all 3D quantities (matching flow resolution prevents interpolating flow vectors)
    maps_width, maps_height = video.get_flow_res()

    for t in range(video.first_frame_idx, video.last_frame_idx + 1):
        # Compute 3D maps
        Vs = video.get_point_cloud(t, resize_res=(maps_width, maps_height))
        flow_3d = video.get_flow_3d(t if t < video.last_frame_idx else t - 1)

        # Create a mask for pixels that have abnormaly high scene flow in camera ray direction
        eye_to_point_vecs = Vs - video.get_camera(t).get_position()
        eye_to_point_vecs = eye_to_point_vecs / np.linalg.norm(eye_to_point_vecs, axis=1)[:,None]
        flow_dot_cam_ray = np.abs(np.einsum('ij,ij->i',eye_to_point_vecs,flow_3d))

        pt_cloud_bb_diag = np.linalg.norm(np.max(Vs, axis=0) - np.min(Vs, axis=0))
        # print("Scene size", pt_cloud_bb_diag)
        depth_flow_is_suspicious = flow_dot_cam_ray > 0.05 * pt_cloud_bb_diag

        depth_flow_mask = depth_flow_is_suspicious.reshape((maps_width, maps_height)).T
        depth_flow_mask_resized = np.ceil(cv2.resize(depth_flow_mask.astype(float), (mask_res_x, mask_res_y),interpolation=cv2.INTER_AREA)).astype(bool)

        # cv2.imshow("depth flow mask",depth_flow_mask)

        # Masks: flow consistency, depth edges
        depth_t_resized = video.get_depth_map(t, resize_res=mask_res)
        depth_mask = mask_high_depth_gradient(depth_t_resized, threshold=0.2)
        feature_mask = depth_mask
        if t + 1 <= video.last_frame_idx:
            # Flow consistency mask
            flow_con = video.get_flow_consistency(t, resize_res=mask_res)
            feature_mask &= flow_con.astype(bool)

        # Erode it a bit and flatten
        feature_mask = ndimage.binary_erosion(feature_mask.astype(int), structure=np.ones((1,1))).astype(bool).T.flatten()

        # Mask places where the depth flow is probably erroneous
        feature_mask &= ~depth_flow_mask_resized.T.flatten()

        all_masks[t - video.first_frame_idx] = feature_mask

    if not os.path.exists(os.path.join(backend_data_path, video.video_name)):
        os.makedirs(os.path.join(backend_data_path, video.video_name))

    np.savez(
        os.path.join(backend_data_path, video.video_name, "masks.npz"), 
        masks=all_masks,
        res=(mask_res_x, mask_res_y))