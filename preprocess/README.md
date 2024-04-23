# Video Doodles preprocessing scripts

## Summary

This repository contains all preprocessing code useful to generate the data used in the VideoDoodles application.

We provide example input data for preprocessing [here](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-raw-data.zip) to make it easy to try out code from this repository. However, if you would like to directly use preprocessed data in the VideoDoodles application, we also provide preprocessed data ([backend data](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-preprocessed-data-backend.zip) and [frontend data](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-preprocessed-data-ui.zip)).

We provide all preprocessing code in order to facilitate reproducing our work in the future. For practical reasons, we based our implementation on a specific cameras/depth/flows input format that was readily available to us at the time. This readme gives a detailed description of this format, and the python scripts show how such raw 3D/motion data needs to be converted for the VideoDoodles application.

## Dependencies
Preprocessing scripts (and in particular the `videowalk`  deep image feature repository) depend on some pip/conda packages. Install with:

```bash
conda create -n video-doodles-preprocess python=3.10
conda activate video-doodles-preprocess

pip install -r requirements.txt
```

We need to pull videowalk as a git module:

```
git submodule update --init
```

## Required input data

We will read input data from a `raw-data` folder:

```
VideoDoodles
		app
    preprocess
    raw-data
```
The `raw-data` folder should contain one folder per video, with the name of the folder matching the video name. Each per-video folder should contain:
```bash
raw-data
    video_name
        frames.npz
        flows.npz
        flows_con.npz
        resized_disps.npz
        refined_cameras.txt
```

The relative or absolute path to this folder can be changed in `default_paths.py`. We provide raw data for a few video [here](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-raw-data.zip). Unzip the archive to get the per-video folders.

## Scripts

Generate all preprocessed data for a video:

```bash
python3 prepare_all.py --vid <video_name> [-E]
```

The flag `-E` causes an export. To visualize 3D point clouds, flows and cameras in a polyscope viewer, remove this flag.

## Output data description

The end result of the preprocessing scripts are two kinds of data:

* "Backend" maps used by the Python backend server (or pure tracking applications). This should be located in `app/backend/data`:

```bash
video_name             # Root folder for the video <video_name>
                       # (1) 3D/flow maps
    maps_dim.npy       # Stores a vector indicating array dimensions of pos and flow maps
                       # values = (nb_frames, maps_res_x, maps_res_y)
    pos.memmap         # An array of 3D points
                       # shape = (nb_frames, maps_res_x * maps_res_y, 3)
    flow.memmap        # An array of 3D scene flow vectors
                       # shape = (nb_frames, maps_res_x * maps_res_y, 3)
    masks.npz          # Contains an array "masks" of boolean flags
                       # shape = (nb_frames, maps_res_x * maps_res_y)
                       
                       # (2) Deep image feature maps
    features_dim.npy   # Stores a vector indicating array dimensions of deep image features
                       # values = (nb_frames, feats_res_x, feats_res_y, latent_dim)
    features.memmap    # An array of deep image features
                       # shape = (nb_frames, feats_res_x * feats_res_y, latent_dim)

                       #( 3) Cameras
    cameras.npz        # Contains arrays/values:
                         #  Ks:                intrinsics, shape = (nb_frames * 3 * 3)
                         #  Rs:                rotations, shape = (nb_frames * 3 * 3)
                         #  ts:                translations, shape = nb_frames * 3)
                         #  res:               resolution of frontend videos, shape = (2,)
                         #  down_scale_factor: scale factor between real scale of 3D scene and frontend UI scale
                         #  near:              camera near plane
                         #  far:               camera far plane
```

* "Frontend" data for the javascript client. This should be located in `app/frontend/public/data`:

```bash
video_name             # Root folder for the video <video_name>
    vid.mp4            # Color video (encoded to support frame-by-frame scrubbing)
    depth_16           # Folder containing all depth frames
        0000.png       #   16-bit normalized depth map for frame 0, encoded on two channels of an 8-bit PNG image
        0001.png
        <...>
    camera.json         # Cameras data: a list of cameras, one per frame:
                       #  {
                       #    rotation:                  camera rotation (Quaternion as a list)
                       #    translation:               camera position (3D vector as a list)
                       #    cameraProjectionTransform: camera projection matrix (4x4 matrix as a row-major list)
                       #    depthRange:                scale of depth maps before normalization (float)
                       #    depthOffset:               offset of depth maps before normalization (float)
                       #  }
```

Data formats were chosen ad hoc to make things easy for myself during development and deployment, for example camera and depth info is "duplicated" in frontend and backend, and also in the form of the 3D point cloud maps: this makes things easier in terms of deployment (no need to have shared data storage between backend Python server and client server) and avoids recomputation of unprojected point clouds in the tracking optimization loop.

Looking at the [frontend](../app/frontend) and [backend](../app/backend) repositories should be helpful in understanding how this data is used in practice.

## Input data description

Parsers for the input data we expect are in the files `videodepth_video.py` and `videodepth_camera.py`. Adapting the preprocessing scripts to match another input data format can be done by adapting these classes. Here is a brief description of each numpy archive, although looking directly at corresponding code in the files `videodepth_*.py` might be equally helpful. The code snippets here are only useful as clarifications, to generate preprocessed data, you may use directly our scripts (see above).

### Image/frames: `frames.npz`

Contains arrays for each frame of the video.

```python
# Reading a frame at index t:
frame_archive = np.load("frames.npz")
frame_t = frame_archive[f"frame_{t:05d}"] # shape: (height, width, 3)
```

### Flows: `flows.npz` and flow consistency masks: `flows_con.npz`

`flows.npz` contains optical flows from one frame to the next, eg `flow_00000_to_00001` is the optical flow from frame `0` to frame `1`. We estimate optical flow from consecutive frames using [RAFT](https://github.com/princeton-vl/RAFT).

`flows_con.npz` contains binary masks that indicate whether at a given pixel forward and backward flows are consistent with each other (see the [RCVD paper](https://robust-cvd.github.io/)). This gives an idea of whether the optical flow -- and in our case, the 3D scene flow -- is trustworthy at a pixel.

```python
# Reading optical flow and flow consistency mask between frames t and t+1:
flow_archive = np.load("flows.npz")
flow_t = flow_archive[f"flow_{t:05d}_to_{t+1:05d}"]

flow_cons_archive = np.load("flows_con.npz")
flow_mask_t = flow_cons_archive[f"consistency_{t:05d}_{t+1:05d}"]
```

### Cameras: `refined_cameras.txt`

A text file with one line per frame + a last line encoding camera focal lengths `fx, fy` for the whole video. Each frame-line has the following format:

```bash
t_x t_y t_z rot_x rot_y rot_z scale shift
```

with `t` the translation vector of the camera (ie, its position in world space) and `rot` its rotation vector. `scale` and `shift` are used to scale and shift the disparity maps (see below). Note: in practice, we have fixed `scale=1` and `shift=0` in all our depth inferrence results, but we assume arbitrary values for the sake of completeness.

The rotations are given in a right handed coordinate system with z forward, -y up (this is the convention [COLMAP](https://colmap.github.io/format.html#images-txt) uses). The script `videodepth_camera.py` shows how to use the camera parameters to unproject a frame+depth to a world space point cloud (eg, see function `unproject_to_world_space`). In `cameras.py` we also show how camera data (extrinsics and intrinsics) can be save as an "OpenGL" style camera that can be loaded in our frontend UI (three.js rendering).

### Depth maps: `resized_disps.npz`

Contains arrays with one disparity map per frame of the video. The disparity maps are inferred with a re-implementation of [Robust Consistent Video Depth Estimation](https://robust-cvd.github.io/). They are consistent across the whole video. The disparity is stored as maps that need to be scaled/shifted by constant values stored in the cameras data file (in practice for our inferred cameras this amounts to an identity transformation).

```python
# Reading a disparity map at index t:
disp_archive = np.load(disparity_npz_path)
disp_t = disp_archive[f"disp_{t:05d}"] # shape: (height, width, 1)
# Rescale to true scale by using data stored in refined_cameras.txt:
disparity = get_camera(t).scale * disp + get_camera(t).shift # note that this amounts to the identity for our cameras
# Convert to depth map:
disparity[disparity < 1e-6] = 1e-6 # prevent division by zero
depth_map = 1.0/disparity
```

## More resources

### Publication

The VideoDoodles system and implementation is described in the associated publication: [webpage](https://em-yu.github.io/research/videodoodles/), [paper](https://www-sop.inria.fr/reves/Basilic/2023/YBNWKB23/VideoDoodles.pdf), [ACM page](https://dl.acm.org/doi/abs/10.1145/3592413).

If this code is useful to your research, please consider citing the publication:

```
@article{videodoodles,
  author = {Yu, Emilie and Blackburn-Matzen, Kevin and Nguyen, Cuong and Wang, Oliver and Habib Kazi, Rubaiat and Bousseau, Adrien},
  title = {VideoDoodles: Hand-Drawn Animations on Videos with Scene-Aware Canvases},
  year = {2023},
  publisher = {Association for Computing Machinery},
  doi = {10.1145/3592413},
  journal = {ACM Trans. Graph.},
  articleno = {54},
  numpages = {12},
}
```

### Contact

Emilie Yu: emiliextyu@gmail.com
