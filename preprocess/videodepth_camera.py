import numpy as np
from scipy.spatial.transform import Rotation

def windowing_matrix(hres, vres, y_up=True):
    if y_up:
        return np.array([
        [ hres/2,  0, hres/2],
        [ 0,  -vres/2, vres/2],
        [0, 0, 1]
        ], dtype=float)
    else:
        return np.array([
        [ hres/2,  0, hres/2],
        [ 0,  vres/2, vres/2],
        [0, 0, 1]
        ], dtype=float)

class Camera:

    # Rotation matrix and intrinsics follow the OpenGL standard: 
    # a right handed coordinate system with -z forward, y up

    t : np.ndarray
    R : np.ndarray
    # K : np.ndarray
    fx : float
    fy : float
    shift : float
    scale : float

    def __init__(
            self, 
            t     : np.ndarray,
            R     : np.ndarray,
            fx    : float,
            fy    : float,
            shift : float,
            scale : float) -> None: 
        '''Create a Camera object from raw data (eg from Colmap and/or depth estimation methods).

        Args: 
            t (np.ndarray): translation vector
            R (np.ndarray): rotation vector (we assume this is given in a right handed coordinate system with z forward, -y up => this is what Colmap does according to this https://colmap.github.io/format.html)
            fx (float)    : focal length in X axis (in NDC)
            fy (float)    : focal length in Y axis (in NDC)
            shift (float) : depth map shift (used to recover true depth values because depth is encoded as normalized values)
            scale (float) : depth map scale (used to recover true depth values because depth is encoded as normalized values)
            width (int)   : resolution in X axis (in pixels)
            height (int)  : resolution in Y axis (in pixels)
        '''

        self.t = t
        self.shift = shift
        self.scale = scale
        self.fx = fx
        self.fy = fy

        # Rotate camera to match openGL convention (-z forward)
        self.R = Rotation.from_rotvec(R).as_matrix() @ Rotation.from_euler('x', 180, degrees=True).as_matrix()

    def K(self, width : int, height : int) -> np.ndarray :
        # Compute K (camera intrinsics) matrix
        K = np.array(((self.fx * width / 2, 0, width // 2 - 0.5), (0, self.fy * height / 2, height // 2 - 0.5), (0, 0, 1)), dtype=np.float64)
        # Change axes of K 
        # The input camera data is in OpenCV standard (z forward, -y up)
        # We want it to work in OpenGL standard
        # (a right handed coordinate system with -z forward, y up)
        axes_change_mat = np.eye(3)
        axes_change_mat[1,1] = -1
        axes_change_mat[2,2] = -1

        return K @ axes_change_mat

    def get_open_gl_projection_matrix(self, near : float, far : float, hres : int, vres : int):
        dimensionless_K = np.linalg.inv(windowing_matrix(hres, vres, y_up=True)) @ self.K(hres, vres)
        gamma = - (far + near) / (far - near)
        beta = -2 * near * far / (far - near)
        dimensionless_K[2, 2] = gamma
        M_gl = np.insert(np.insert(dimensionless_K, 3, [0, 0, -1], axis = 0), 3, [0, 0, beta, 0], axis = 1)
        return M_gl
    
    def unproject_to_camera_space(
            self, 
            xs    : np.ndarray,
            ys    : np.ndarray,
            depths: np.ndarray,
            width : int,
            height: int
        ): 
        pix_coords = np.column_stack([xs, ys, np.ones(xs.shape)])
        return (np.linalg.inv(self.K(width, height)) @ pix_coords.T).T * depths.flatten()[:, None]

    def unproject_to_world_space(
            self, 
            xs    : np.ndarray,
            ys    : np.ndarray,
            depths: np.ndarray,
            width : int,
            height: int
    ):
        # Transpose R because we have row vectors that we right-multiply
        # original formula for 1 point : R * cameraPosition(...) + t
        Vs_cam = self.unproject_to_camera_space(xs, ys, depths, width, height)
        return Vs_cam @ self.R.T + self.t
    
    def get_position(self):
        return self.t
    
    # Forward is -Z
    def get_forward(self):
        return - self.R[:, 2]