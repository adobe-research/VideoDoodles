# Video Doodles backend and tracking code

## Dependencies and required input data

- [x] **Install dependencies**

```bash
conda create -n video-doodles-backend python=3.10
conda activate video-doodles-backend

pip install -r requirements.txt
```

Note: `polyscope` and `opencv-python` are used only for debug visualisation purposes and can be omitted when deploying the backend to be used without visualisation.

- [x] **Provide videos data**

We provide data for 16 videos, please [download the archive](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-preprocessed-data-backend.zip) and extract into `data` folder:

```
backend
    data
        blackswan
        car-roundabout
        ...
        train
```

## Running the server

To run locally:

```bash
cd app/backend
python3 app.py
# This exposes websocket ports at: ws://localhost:8001/
```

## Running tracking scripts

The tracking scripts can be called in standalone mode, to facilitate testing or evaluation.

Note that to visualize the results, we need to read in color frames and binary masks which you should download separately ([download link](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-raw-data.zip), extract in `VideoDoodles/raw-data`). Alternatively, running with the flag `-H` skips visualization.

```bash
cd app/backend

# Test the motion path solve ("Tracking 3D positions" in Sec. 5.2 of the paper)
python3 -m scripts.test_find_motion_path --kf train_1kf

# Test the 3D trajectory optimization ("Recovering stable, high-resolution trajectories" of Sec. 5.2.)
python3 -m scripts.test_optimize_trajectory --kf train_1kf

# Export the trajectory result so that it can be used for orientations estimation (-E flag)
python3 -m scripts.test_optimize_trajectory --kf train_orientations_1kf -E

# Test orientations optimization
python3 -m scripts.test_orientations --traj train_orientations_1kf
```

The keyframe record files (eg `train_1kf`) can be created through the web UI by clicking the `Export Keyframes` button (available on the right-side bar when a canvas is selected in `Edit` mode).

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