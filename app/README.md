# Video Doodles web application

This folder contains the frontend and backend code to run the Video Doodles web application.

* `backend`: a Python websocket server that awaits calls to solve for 3D trajectories. This folder contains all code pertaining to 3D tracking, both in reaction to frontend interactions as well as Python scripts useful to test or play with 3D tracking.
* `frontend`: a web application based on [Svelte](https://svelte.dev/), served by a simple Python web server.

## Data

Download data for 16 videos:

* Frontend data (1GB): [download here](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-preprocessed-data-ui.zip)
* Backend data (10GB): [download here](https://repo-sam.inria.fr/d3/VideoDoodles/video-doodles-preprocessed-data-backend.zip)

Frontend data must be unzipped under `app/frontend/public/data` and backend data under `app/backend/data`.

## Quick start with Docker

We provide a simple way to run the whole application (locally or on a remote server) via Docker. After installing Docker, run:

```bash
cd app
docker compose up --build -d
```

This will build two Docker images (`video-doodles-app-backend` and `video-doodles-app-ui`), based on the `Dockerfile` of each folder (flag `--build`, it can be ommitted if your images are already built). Each image will have all dependencies installed and the UI webpage content will be built via `npm` based on source code. Then Docker will start running one container for each image (in detached mode, flag `-d`), and launch the Python servers.

At this point, if both containers were started successfully, you should be able to see the app at: http://localhost:80

To see logs from the containers:

```bash
# This will list all running and exited containers, so you can use it to see if both containers have started fine
docker ps -a
# should give something like:
CONTAINER ID   IMAGE                       COMMAND                  CREATED          STATUS          PORTS                    NAMES
06bf4ac29338   app-backend                 "python3 -u app.py"      16 minutes ago   Up 16 minutes   0.0.0.0:8001->8001/tcp   app-backend-1
848cf6c69995   app-frontend                "tiny-http-server --…"   21 minutes ago   Up 21 minutes   0.0.0.0:80->8000/tcp     app-frontend-1

# Follow the logs of backend container (Ctrl+C to stop following):
docker logs -f app-backend-1
# Stream of logs...
```

A container that has exited means that an error arose. Checking the logs can help resolve that: `docker logs <container-name>`

Stop containers when you are done:

```bash
# Stop containers
docker stop app-backend-1
docker stop app-frontend-1
# Remove them
docker container prune
```

Please refer to `docker-compose.yml` and `Dockerfile` files for more details on the configuration.

## How to use the web application

Please watch the tutorial: https://youtu.be/hD5wZGVG6nQ

We added a feature to export keyframes from a given canvas, in order to use them as offline tracking targets. The button `Export Keyframes` is available on the right-side bar when a canvas is selected in `Edit` mode.

## Expected hardware for interactive rates

The Python backend code needs to read heavy data files for tracking, our current unoptimized implementation will thus work best (ie, fast) with ample CPU memory available. We ran our user evaluations on a VM with 8GB RAM, and performance tests on a Macbook with 16GB RAM. Lower configs should still work, albeit quite slow. With Docker, one might run into lack of available RAM allocated to Docker, so we would encourage people who want to dig deeper to look into each of the individual folders' README to find instructions to run the code directly from their local environment.

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