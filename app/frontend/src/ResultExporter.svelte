<script>
    import {onMount, onDestroy, createEventDispatcher, afterUpdate, tick} from 'svelte';
    import * as THREE from 'three';
    import { CanvasCapture } from 'canvas-capture';

    import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
    import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
    import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
    import { FXAAShader } from "three/examples/jsm/shaders/FXAAShader.js";

    import FullscreenOverlay from './components/FullscreenOverlay.svelte';

    import { animationController } from "./AnimationController.js";

    import { clipFrames, time, clipName } from './store.js';

    import { sessionLog } from './SessionLog.js';


    // export let threeScene;
    // export let videoTex;
    // export let threeCamera;

    // export let active = true;
    export const triggerExport = () => {startExport()}

    let threeExportDOMElement;
    let renderer;
    let composer;
    let aaPass;

    let dlAnchorElem;

    export let renderingFrames = false;
    let preparingDownload = false;

    let exportProgressRatio = 0;



    // Called by the "video loaded" event
    // we want to set the resolution to be the same as that of the video
    export const setResolution = (videoTex) => {
        if (!renderer || ! composer || !videoTex)
            return;

        let videoWidth = videoTex.source.data.videoWidth;
        let videoHeight = videoTex.source.data.videoHeight;

        console.log("setting export video dimension");
        // console.log(videoWidth);
        // console.log(videoHeight);

        renderer.setSize(videoWidth, videoHeight, true);
        composer.setSize(videoWidth, videoHeight);

        aaPass.material.uniforms[ 'resolution' ].value.x = 1 / videoWidth;
        aaPass.material.uniforms[ 'resolution' ].value.y = 1 / videoHeight;

    }

    // Called by the "video frame seeking success" event
    export const exportFrame = () => {
        if (!renderingFrames)
            return;


        const frame = $clipFrames[$time];

        if (!frame.camera) {
            console.error("cannot export, scene and camera not loaded.")
            return;
        }

        // Set camera for every pass
        composer.passes.forEach((pass) => {
            pass.camera = frame.camera;
        })

        // Render three.js scene
        composer.render();

        // const t1 = performance.now();
        // console.log(`Rendering took ${t1 - t0} milliseconds.`);

        console.log(`rendering frame ${$time} from ResultExporter`);

        
        // Export frame
        CanvasCapture.recordFrame();
        
        // Increment time (this will trigger seeking the next frame in VideoManager)
        if ($time < $clipFrames.length - 1)
            time.update((t) => t + 1);
        else {
            console.log("finished rendering frames");
            renderingFrames = false;
            CanvasCapture.stopRecord();
            preparingDownload = true;

        }
    }


    export const onSceneInitialisation = (scene) => {

        renderer = new THREE.WebGLRenderer({ canvas: threeExportDOMElement, preserveDrawingBuffer: true  });
        renderer.setSize( window.innerWidth, window.innerHeight );

        composer = new EffectComposer( renderer );

        // This camera is just used to initialize the renderpass
        let camera = new THREE.PerspectiveCamera(
            75,    // fov
            2,     // aspect (this will be updated by resizeRenderToDisplay to match the canvas size anyway)
            0.01,   // near
            100.0   // far
        );

        const renderPass = new RenderPass( scene, camera );
        composer.addPass( renderPass );

        aaPass = new ShaderPass( FXAAShader );
        composer.addPass(aaPass);



        // Recording
        // Initialize and pass in canvas.
        CanvasCapture.init(
            threeExportDOMElement,
            { showRecDot: true },
        );

        // console.log(CanvasCapture);

    };

    function getFileName() {
        return `${new Date().toISOString()}_${$clipName}`;
    }

    function startExport() {
        console.log("start export");
        exportCanvasesData();
        exportLog();
        renderingFrames = true;

        CanvasCapture.beginJPEGFramesRecord({
            name: getFileName(),
            onExportProgress: (progress) => { exportProgressRatio = progress; },
            onExportFinish: () => { preparingDownload = false; }
        });

        if ($time == 0)
            exportFrame();
        else
            time.update((t) => 0);


    }

    function exportCanvasesData() {
        let data = animationController.exportCurrentCanvases();
        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        dlAnchorElem.setAttribute("href",     dataStr     );
        dlAnchorElem.setAttribute("download", `${getFileName()}_result.json`);
        dlAnchorElem.click();
    }

    function exportLog() {
        let data = sessionLog.export();
        let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        dlAnchorElem.setAttribute("href",     dataStr     );
        dlAnchorElem.setAttribute("download", `${getFileName()}_log.json`);
        dlAnchorElem.click();
    }



</script>

<style>
    #three-export-scene {
        display: none;
    }
</style>


<!-- <svelte:window 
    on:keydown={(e) => {if (active && e.code == "KeyS") { e.preventDefault();  startExport(); } }}
/> -->

{#if (renderingFrames || preparingDownload)}
    <FullscreenOverlay priority={20}>
        Exporting video...
        <br/>
        {#if renderingFrames}
            Rendering frame: {$time + 1} / {$clipFrames.length}
        {/if}
        {#if preparingDownload}
            Preparing file to download: {(exportProgressRatio * 100).toFixed(0)} %
        {/if}
    </FullscreenOverlay>
{/if}

<canvas id="three-export-scene" bind:this={threeExportDOMElement}></canvas>
<a id="downloadAnchorElem" style="display:none" bind:this={dlAnchorElem}>

</a>