# Video Doodles frontend

## Dependencies and required input data

- [x] **Install dependencies**

We use npm to manage dependencies, so to build the app locally please install Node.js/npm: https://docs.npmjs.com/downloading-and-installing-node-js-and-npm. Then run:

```bash
cd app/frontend
npm install
```

- [x] **Provide videos data**

We provide data for 16 videos, please [download the archive](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-preprocessed-data-ui.zip) and extract into `frontend/public/data` folder, so that it looks like:

```bash
public
  data
    video_name             # Root folder for the video <video_name>
        vid.mp4            
        depth_16           # Folder containing all depth frames
        camera.json
    ...
```

## Running the web app

Install and run locally:

```bash
npm run dev
# Find it at http://localhost:8080
```

Build and serve (to deploy on some server):

```bash
npm run build
cd public
python3 -m http.server
# Find it at http://localhost:8000
```

Note: the app will not work correctly (ie, it can't place canvases correctly) unless the backend server is also running. See [backend repo](../backend) for instructions to run it.

## Exporting results

Video doodles results can be exported from the UI. In **View** mode click the **Export** button. This will download 3 files to your download folder (you might need to authorize the website to download multiple files in the browser):

```bash
<timestamp>_<video-name>.zip         # color frames of the video
<timestamp>_<video-name>_result.json # save of the result, can be reloaded in the app
<timestamp>_<video-name>_log.json    # log of the session, used for analysis purpose during the user study
```

The frames can be made into a video again, eg with ffmpeg:

```bash
# Uncompress frames
unzip <frames_zip_file> -d temp
# Render to a video
ffmpeg -y -framerate 20 -i 'temp/frame_%d.jpg' -c:v libx264 -pix_fmt yuv420p video.mp4
# Optional: delete the temp folder
yes | rm temp/*
```

We added a feature to export keyframes from a given canvas, in order to use them as offline tracking targets. The button `Export Keyframes` is available on the right-side bar when a canvas is selected in `Edit` mode.

## What's in there

This application features:

* A [three.js](https://threejs.org/) renderer that composites video frames with rendered 3D objects from a specified camera (both extrinsic and intrinsic parameters are set from a camera model estimated with COLMAP, see [preprocessing code](../../preprocess) for more details about the conversion), using estimated depth maps to render occlusions. See `Viewport.svelte` for the `three.js` scene, and `Frame.js` for details on camera parameters and depth/color buffers. See `shaders/fragment.glsl` for depth compositing.
* A `svg` stacked on top of the `three.js` renderer canvas, that contains 2D gizmos corresponding to the `AnimatedCanvas` objects of the application. See `Viewport.svelte` and `CanvasGizmo.js`.
* A timeline that displays keyframes from the `AnimatedCanvas` objects, and can be navigated by clicking. See `KeyframeTimeline.svelte`.
* A drawing canvas that displays a remapped view into the scene, as seen "from the canvas" to enable sketching in context. See `DrawingCanvas.svelte` and `SceneViewFromCanvas.svelte`.
* A super simple frame-by-frame animation system to define multi-frame animation loops. See `SketchFramesTimeline.svelte` and `SketchAnimationClip.js`.
* A link to a backend server through websocket, to exchange info via json strings. See `websocket.js`.

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