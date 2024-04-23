import numpy as np
from typing import List, Tuple
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp

def normalize(vectors):
    if len(vectors.shape) > 1:
        norms = np.linalg.norm(vectors, axis = 1)
        norms[norms < 1e-8] = 1
        vs = vectors / norms[:, None]
        return vs
    else:
        norm = np.linalg.norm(vectors)
        norm = max(norm, 1e-8)
        return vectors / norm

def mse_mat(A : np.ndarray, B : np.ndarray) -> np.ndarray :
    '''
    Computes a matrix C filled with the mean squared error between values of matrices A and B along their last axis.

    C[i, j] = \sum_k (A[i, k] - B[j, k])**2

    Args:
        A (np.ndarray): a matrix with dimensions (N, k)
        B (np.ndarray): a matrix with dimensions (M, k)

    Returns:
        np.ndarray: a matrix with dimensions (N, M)
    '''
    if (A.shape[0] == 1 or B.shape[0] == 1):
        mse = np.sum((A - B)**2, axis=-1)
        return mse.reshape((A.shape[0], B.shape[0]))
    else:
        mse = np.einsum('ij,ij->i',A,A)[:,None] + np.einsum('ij,ij->i',B,B) - \
                                                        2*np.dot(A,B.T)
        
        # Prevent very small negative values /!\ they can arise due to floating point errors
        mse = np.clip(mse, a_min=0, a_max=None)
        
        return mse


def assign_edge_indices(
      prev_indices       : np.ndarray,
      curr_indices       : np.ndarray,
      current_nz_data_idx: int,
      graph_matrix_row   : np.ndarray,
      graph_matrix_col   : np.ndarray
    ) -> None            : 
    '''
    Adds values to sparse matrix data (graph_matrix_row, graph_matrix_col) to represent edges going from each node i in prev_indices to each node j in curr_indices

    Args:
        prev_indices (np.ndarray): source node indices
        curr_indices (np.ndarray): target node indices
        current_nz_data_idx (int): lowest index in graph matrix data arrays that is unassigned yet
        graph_matrix_row (np.ndarray): sparse graph matrix data (non-zero row indices)
        graph_matrix_col (np.ndarray): sparse graph matrix data (non-zero column indices)
    '''

    # s = time.time()

    for i, idx in enumerate(prev_indices):
        start_idx = current_nz_data_idx + i * len(curr_indices)
        end_idx = start_idx + len(curr_indices)
        graph_matrix_row[start_idx:end_idx] = idx
        graph_matrix_col[start_idx:end_idx] = curr_indices
    # print("time to assign all edge indices (loop)", time.time() - s)


def compute_all_edge_weights(
    prev_pos_3d  : np.ndarray,
    prev_features: np.ndarray,
    prev_indices : np.ndarray,

    flow_prev_to_curr: np.ndarray,

    curr_pos_3d  : np.ndarray,
    curr_features: np.ndarray,
    curr_indices : np.ndarray,

    curr_features_to_kf:np.ndarray, 

    proximity_weight                : float,
    feature_similarity_weight       : float,
    target_feature_similarity_weight: float,

    graph_matrix_data: np.ndarray,
    graph_matrix_row : np.ndarray,
    graph_matrix_col : np.ndarray,

    current_nz_data_idx:int
    ) -> int:
    '''
    Computes edge weights between nodes at frame t and nodes at frame t+1.
    For nodes i (at t) and j (at t+1):
    w_ij = proximity_weight * (pos_i + flow_i - pos_j)**2  \
            + feature_similarity_weight * (feat_i - feat_j)**2 \
            + target_feature_similarity_weight * (feat_j - feat_closest_kf)**2

    Note: in the final implementation, we always set:
        proximity_weight                 = 1 ,
        feature_similarity_weight        = 0 ,
        target_feature_similarity_weight = 0 .

    Assigns edge weights and edge indices in the arrays describing the sparse graph matrix.
    

    Args:
        prev_pos_3d (np.ndarray): nodes 3D positions at frame t
        prev_features (np.ndarray): nodes image features at frame t
        prev_indices (np.ndarray): nodes indices at frame t
        flow_prev_to_curr (np.ndarray): 3D flows at nodes at frame t (flow from t to t+1)
        curr_pos_3d (np.ndarray): nodes 3D positions at frame t+1
        curr_features (np.ndarray): nodes image features at frame t+1
        curr_indices (np.ndarray): nodes indices at frame t+1
        curr_features_to_kf (np.ndarray): mse of the image feature of each node to the most similar neighboring keyframe image feature 
        proximity_weight (float): weight of the 3D distance term in the optimization
        feature_similarity_weight (float): weight of the image feature term (between nodes) in the optimization
        target_feature_similarity_weight (float): weight of the image feature term (between a node and target keyframes) in the optimization
        graph_matrix_data (np.ndarray): sparse graph matrix data (non-zero data values)
        graph_matrix_row (np.ndarray): sparse graph matrix data (non-zero row indices)
        graph_matrix_col (np.ndarray): sparse graph matrix data (non-zero column indices)
        current_nz_data_idx (int): lowest index in graph matrix data arrays that is unassigned yet

    Returns:
        int: lowest index in graph matrix data arrays that is unassigned after the assignment of new edges
    '''

    # s = time.time()
    assign_edge_indices(prev_indices, curr_indices, current_nz_data_idx, graph_matrix_row, graph_matrix_col)
    end_idx = current_nz_data_idx + len(prev_indices) * len(curr_indices)
    # print("time assigning indices", time.time() - s)

    # print("count src =", len(prev_indices))
    # print("count dst =", len(curr_indices))

    prev_pos_advected = prev_pos_3d + flow_prev_to_curr

    # print(prev_pos_advected.shape, curr_pos_3d.shape, curr_pos_3d.dtype, prev_pos_advected.dtype)

    pos_mat = mse_mat(prev_pos_advected, curr_pos_3d)

    # print(np.min(pos_mat))

    # print(feats_mat.shape, pos_mat.shape, curr_features_to_kf.shape)

    weights_mat = proximity_weight * pos_mat

    if feature_similarity_weight > 0:
        feats_mat = mse_mat(prev_features, curr_features)
        weights_mat += feature_similarity_weight * feats_mat 

    if target_feature_similarity_weight > 0:
        weights_mat += target_feature_similarity_weight * curr_features_to_kf.reshape((1, -1))

    graph_matrix_data[current_nz_data_idx:end_idx] = weights_mat.flatten()

    # print("computing edge weights values", time.time() - start_all)
    

    return end_idx




def sparse_add_value(
        value      : float,
        i          : int,
        j          : int,
        data       : List[float],
        row_indices: List[int],
        col_indices: List[int],
        flat       : bool = False
    ) -> None: 
    '''
    Add a non-zero value at [i, j] to the sparse matrix representation (data, row indices, column indices).
    We assume that this final sparse matrix as a shape (3xN, 3xN), with N the total number of 3D points.
    If flat is set to true, we can set values in the sparse matrix by indexing based on point index (and set the same value for all 3 diagonal coords of this point).

    Args:
        value (float): _description_
        i (int): _description_
        j (int): _description_
        data (List[float]): _description_
        row_indices (List[int]): _description_
        col_indices (List[int]): _description_
        flat (bool, optional): _description_. Defaults to False.
    '''
    if flat:
        data.extend(np.repeat(value, 3))
        row_indices.extend([3 * i, 3 * i + 1, 3 * i + 2])
        col_indices.extend([3 * j, 3 * j + 1, 3 * j + 2])
    else:
        data.append(value)
        row_indices.append(i)
        col_indices.append(j)



def get_camera_ray(
        pt_2d: np.ndarray, 
        frame_idx: int,
        cameras_data: dict
    ) -> Tuple[np.ndarray, np.ndarray]:
    '''For a given point in screen space and a given frame/camera, return the position of the camera at this frame,
    and the 3D direction vector in which the ray is going through that point.

    Args:
        pt_2d (np.ndarray): _description_
        frame_idx (int): _description_
        cameras_data (dict): _description_

    Returns:
        Tuple[np.ndarray, np.ndarray: camera ray origin, camera ray direction
    '''
    # R = cameras_data["RTs"][frame_idx][:3, :3].T
    # translation = -R @ cameras_data["RTs"][frame_idx][:3, 3]

    R = cameras_data["Rs"][frame_idx]
    translation = cameras_data["ts"][frame_idx]

    camera_ray_origin = translation * cameras_data["down_scale_factor"]
    
    # Transpose R because we have row vectors that we right-multiply
    # original formula for 1 point : R * cameraPosition(...) + t
    cam_res = cameras_data["res"]
    K = cameras_data["Ks"][frame_idx]
    pix_coords = np.array([pt_2d[0] * cam_res[0], pt_2d[1] * cam_res[1], 1])
    pix_cam = np.linalg.inv(K) @ pix_coords * cameras_data["near"]
    unproj_pt_3d = (R @ pix_cam + translation) * cameras_data["down_scale_factor"]

    camera_ray_dir = unproj_pt_3d - camera_ray_origin
    camera_ray_dir /= np.linalg.norm(camera_ray_dir)

    return camera_ray_origin, camera_ray_dir



# Spherical Linear Interpolation of Rotations
def orientation_slerp(
    keyframes: List[dict],
    start_frame: int, 
    end_frame: int
    ):

    kf_times = []
    kf_rot = []

    clip_length = end_frame - start_frame + 1

    for kf in keyframes:
        if "rot_mat" in kf.keys():

            kf_times.append(kf["t"] - start_frame)
            kf_rot.append(kf["rot_mat"])

    if len(kf_times) < 1:
        # If no keyframes, return the identity
        return np.tile(np.eye(3), (clip_length, 1, 1))
    elif len(kf_times) == 1:
        # Repeat same rotation everywhere
        return np.tile(kf_rot[0], (clip_length, 1, 1))
    else:
        # Interpolate rotations (for frames between first and last kf, both inclusive)
        key_rots = R.from_matrix(np.array(kf_rot))
        slerp = Slerp(kf_times, key_rots)

        first_kf = np.min(kf_times)
        last_kf = np.max(kf_times)

        interp_rots = slerp(np.arange(first_kf, last_kf + 1)).as_matrix()

        first_kf += start_frame
        last_kf += start_frame

        # Pad beginning and end
        if (first_kf) > start_frame:
            start_pad_mats = np.tile(interp_rots[0], (first_kf - start_frame, 1, 1))
            interp_rots = np.row_stack([start_pad_mats, interp_rots])
        if (last_kf) < end_frame:
            end_pad_mats = np.tile(interp_rots[-1], (end_frame - last_kf, 1, 1))
            interp_rots = np.row_stack([interp_rots, end_pad_mats])

        return interp_rots
