<script>
    import {onMount, onDestroy, afterUpdate, createEventDispatcher} from 'svelte';
    import { FileLoader, VideoTexture, TextureLoader, LinearFilter, NearestFilter } from "three";

    import Frame from "./Frame";
    import FullscreenOverlay from './components/FullscreenOverlay.svelte';
    import { clipFrames, time, clipName, criticalErrorMessage } from './store.js';


    const BASE_URL = "data";

    export let tex;
    export let videoFrame = undefined;

    let stackedVideo;

    let loading = false;
    let loadingProgress = 0;

    $: setFrame($time);

    $: changeFootage($clipName);

    const videoDispatch= createEventDispatcher();

    const fileLoader = new FileLoader();
    const textureLoader = new TextureLoader();


    onMount(() => {
        stackedVideo = document.getElementById( 'stacked_vid' );

        stackedVideo.addEventListener('loadeddata', (event) => {
            console.log('The video has loaded.');
            // Dispose of useless textures
            if (tex) {
                tex.dispose();
            }
            // tex = new VideoTexture( {video: stackedVideo, minFilter: NearestFilter, magFilter: NearestFilter  });
            tex = new VideoTexture(stackedVideo);
            tex.minFilter = LinearFilter;
            tex.magFilter = LinearFilter;
            stackedVideo.currentTime = 0;
            videoDispatch('load');
        });

        stackedVideo.addEventListener('error', (e) => {
            console.error(e);
            criticalErrorMessage.set("Can't load video file at: " + stackedVideo.src);
            // Dispose of useless textures
            if (tex) {
                tex.dispose();
            }
        });

        stackedVideo.addEventListener('timeupdate', (event) => {
            if (tex) {
                console.log('The currentTime attribute has been updated. Again.');
                tex.needsUpdate = true;
                videoFrame = $time;
                videoDispatch('update');
            }
        });
    })

    const setFrame = (frameIdx) => {
        // console.log("set frame " + frameIdx);
        if (!stackedVideo)
            return;
        // Compute the time based on a 25fps frame rate
        let t = frameIdx * 1.0/25;
        stackedVideo.currentTime = t;
        // timeSync = false;
    }


    function changeFootage(videoClip) {
        loading = true;
        loadingProgress = 0;
        // Load camera data
        const url = BASE_URL + "/" + videoClip + "/camera.json";
        const camPromise = fileLoader.load(
            url,
            (cameraDataJson) => {
                // console.log(cameraDataJson);
                const cameraData = JSON.parse(cameraDataJson);
                const newFrames = [];
                cameraData.forEach((cam, frameIdx) => {
                    newFrames.push(new Frame(frameIdx, cam));
                });

                // Set video and load it
                stackedVideo.src = BASE_URL + "/" + $clipName + "/vid.mp4";
                console.log("loading " + stackedVideo.src);
                stackedVideo.load();

                loadDepthFrames(newFrames);
            },
            () => {}, // on progress
            (e) => {
                console.error(e);
                criticalErrorMessage.set("Can't load video camera data file at: " + url);
            }
        );

    }

    function loadDepthFrames(frames) {
        // Load depth frames
        const framesCount = frames.length;
        const allDepthPromises = frames.map((frame) => {
        return new Promise((resolve, reject) => {
            const depthUrl =  BASE_URL + "/" + $clipName + "/depth_16" + `/${String(frame.time).padStart(4, '0')}.png`;
            textureLoader.load(
                depthUrl,
                (tex) => { loadingProgress += (100/framesCount) ; console.log("loaded frame " + frame.time); frame.setDepth(tex); resolve(tex); },
                () => {},
                (e) => { console.error("Error loading depth frame at: " + depthUrl); reject(e); }
            );
            })
        });

        Promise.all(allDepthPromises).then(() => {
            console.log("loaded all depth frames");
            // If any, delete all previous frames
            // $clipFrames.forEach((frame) => frame.dispose());
            clipFrames.update(() => frames );
            loading = false;
        })
    }

</script>

<style>
    .hidden {
        display: none;
    }
</style>

{#if loading}
    <FullscreenOverlay opacity={1}>
        Loading new video: 
        <br/>
        {loadingProgress.toFixed(0)} %
    </FullscreenOverlay>
{/if}

<div class="hidden">

    <video id="stacked_vid">
        <!-- <source src="{BASE_URL}/{$clipName}/stacked.mp4"> -->
        <track kind="captions">
    </video>

</div>