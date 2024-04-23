import os
import numpy as np
import cv2


from videodepth_video import VideoData

max_quantile = 0.8


def unpackbits(x, num_bits):
    if np.issubdtype(x.dtype, np.floating):
        raise ValueError("numpy data type needs to be int-like")
    xshape = list(x.shape)
    x = x.reshape([-1, 1])
    mask = 2**np.arange(num_bits, dtype=x.dtype).reshape([1, num_bits])
    return (x & mask).astype(bool).astype(int).reshape(xshape + [num_bits])

# This function packs a WxHx1 array of 16 bits numbers into a WxHx3 array of 8 bit numbers
# by packing bits in the first and second channel (ie, blue and green channel of a RGB image).
# We do this because web browsers can only read 8 bit images
def encode_16bit_to_8bit_image(arr_16, filepath):
    arr_bits = unpackbits(arr_16, 16)
    arr_lsb = arr_bits[:,:,:8]
    arr_msb = arr_bits[:,:,8:]

    # print(arr_lsb.shape, arr_msb.shape)

    b = np.packbits(arr_msb, axis=-1, bitorder='little')
    g = np.packbits(arr_lsb, axis=-1, bitorder='little')

    im = np.concatenate([
        b,
        g,
        np.zeros((b.shape[0], b.shape[1], 1))
    ], axis=-1)

    cv2.imwrite(filepath + ".png", im)


def prepare_depth_maps(video : VideoData, ui_data_path : str):

    depth_out_folder = os.path.join(ui_data_path, video.video_name, "depth_16")
    if not os.path.exists(depth_out_folder):
        os.makedirs(depth_out_folder)

    for fid in range(video.first_frame_idx, video.last_frame_idx + 1):
        depth_map = video.get_depth_map(fid) / video.down_scale_factor

        # Export scaled depth
        # - Normalize
        depth_scaled = (depth_map - video.depth_offset) / video.depth_range
        # - Clip to [0, 1]
        depth_scaled = np.clip(depth_scaled, 0, 1)
        # - Map to the range between the integers '0000000000000000' and '1111111111111111' (in binary)
        depth_scaled_uint16 = np.uint16(depth_scaled * 65535)
        # - Encode these 16 bits binary numbers as 8 bits x 3 channels RGB images
        encode_16bit_to_8bit_image(depth_scaled_uint16, os.path.join(depth_out_folder, f"{fid - video.first_frame_idx:04d}"))