import numpy as np
import os

from .paths import backend_data_root_folder


def index_into_data(pixels, pixel_res, data_res):

    rescaled_pixels = np.round(pixels * np.array([data_res[0]/pixel_res[0], data_res[1]/pixel_res[1]])).astype(int)
    rescaled_pixels = np.clip(rescaled_pixels, [0, 0], [data_res[0] - 1, data_res[1] - 1]).astype(int)

    flat_indices = np.ravel_multi_index([rescaled_pixels[:, 0], rescaled_pixels[:, 1]], (data_res[0], data_res[1]))
    return flat_indices

def get_maps_dims(video_clip):
    return np.load(os.path.join(backend_data_root_folder, video_clip, "maps_dim.npy"))

def get_positions(video_clip, nb_frames, maps_res):
    maps_res_x, maps_res_y = maps_res
    archive_shape = (nb_frames, maps_res_x * maps_res_y, 3)
    pos_3d_archive = np.memmap(os.path.join(backend_data_root_folder, video_clip, "pos.memmap"), mode='r', shape=archive_shape, dtype=np.float64)

    return pos_3d_archive

def get_flows(video_clip, nb_frames, maps_res):
    maps_res_x, maps_res_y = maps_res
    archive_shape = (nb_frames, maps_res_x * maps_res_y, 3)
    flow_3d_archive = np.memmap(os.path.join(backend_data_root_folder, video_clip, "flow.memmap"), mode='r', shape=archive_shape, dtype=np.float64)

    return flow_3d_archive

def get_features_dims(video_clip):
    return np.load(os.path.join(backend_data_root_folder, video_clip, "features_dim.npy"))

def get_features(video_clip, nb_frames, features_res, latent_dimension):
    res_x, res_y = features_res
    archive_shape = (nb_frames, res_x * res_y, latent_dimension)
    feats = np.memmap(os.path.join(backend_data_root_folder, video_clip, "features.memmap"), mode='r', shape=archive_shape, dtype=np.float32)
    return feats


def get_3D_point(video_clip, pt, frame_idx, res_x, res_y):

    total_nb_frames, maps_res_x, maps_res_y = get_maps_dims(video_clip)
    archive_res = (maps_res_x, maps_res_y)
    pos_3d_archive = get_positions(video_clip, total_nb_frames, archive_res)

    pos_3d = pos_3d_archive[(frame_idx, index_into_data(pt.reshape((1, 2)), (res_x, res_y), archive_res))]
    
    return pos_3d[0]


def arrange_colors(colors):
    height, width, _ = colors.shape
    colors = np.transpose(colors, (1, 0, 2))
    colors = colors.reshape((width*height, 3))
    colors = colors[:, ::-1]
    return colors