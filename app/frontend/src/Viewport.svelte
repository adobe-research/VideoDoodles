<script>
    import {onMount, onDestroy, createEventDispatcher, afterUpdate, tick} from 'svelte';
    import * as d3 from "d3";
    import * as THREE from 'three';

    import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
    import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
    import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
    import { FXAAShader } from "three/examples/jsm/shaders/FXAAShader.js";

    // import { ThickenStrokesPass } from "./ThickenStrokesPass.js";
    // import { VisualizeDepthPass } from "./VisualizeDepthPass.js";

    import VideoManager from "./VideoManager.svelte";
    import ResultExporter from './ResultExporter.svelte';

    import { animationController, saveToLoad } from "./AnimationController.js";

    import vertexShader from './shaders/vertex.glsl';
    import fragmentShader from './shaders/fragment.glsl';

    import { clipFrames, time, clipName } from './store.js';

    import { LogActionType, sessionLog } from "./SessionLog.js";


    export let parameters;
    export let editTool;
    export let viewportImage;
    export let threeDOMElement;

    export let triggerExport;

    let { animatedCanvases } = animationController;


    // $ : $time, $animatedCanvases, render();
    // $ : $clipName, initViewport();
    $ : $clipFrames, $time, onFrameChange($time);
    $ : onParametersChange(parameters);
    
    $ : $animatedCanvases, registerCanvases(), drawGizmos(), render();

    // DOM elements
    let viewportContainer;
    let viewportWidth, viewportHeight;
    let dimensionsNeedUpdate = false;

    let videoTex;
    let loadedVideoFrame;

    $: viewportWidth, viewportHeight, dimensionsNeedUpdate = true;


    let svg;

    // let frameHelpers = new THREE.Object3D();

    let canvasContainer = new THREE.Object3D();
    canvasContainer.layers.enable(0);
    canvasContainer.layers.enable(1);

    let scene;
    let renderer;
    let composer;
    let thickenStrokePostProcessingPass;
    let depthVisPass;
    let aaPass;

    let viewPlaneMat;
    let viewPlaneGeom;

    // let exportFrames = false;

    // Exporter variables and methods
    let renderingFramesForExport = false;
    let initialiseExporter;
    let setExporterResolution;
    let exportNextFrame;


    const dispatch = createEventDispatcher();

    function registerCanvases() {
        canvasContainer.clear();
        if ($animatedCanvases !== undefined) {
            Object.values($animatedCanvases).forEach((animatedCanvas) => {
                // console.log(animatedCanvas)
                canvasContainer.add( animatedCanvas.canvas.getObject() )
            });
        }
    }

    function updateCanvasesAppearance(debugView) {
        Object.values($animatedCanvases).forEach((animatedCanvas) => {
            // animatedCanvas.canvas.setBackgroundOpacity(backgroundOpacity);
            animatedCanvas.canvas.setDebugView(debugView);
        });
    }

    function drawGizmos() {
        // if (parameters.mode.value === "view" )
        //     return;
        if (!svg)
            return;

        let frame = $clipFrames[$time];
        if (!frame)
            return;

        console.log("redraw gizmos");

        // Show Gizmos of canvases
        animationController.drawGizmos(parameters.mode.value, editTool );
        // animationController.drawGizmos();
    }

    function onFrameChange(time) {

        if (!renderer)
            return;

        if (time > $clipFrames.length)
            return;

        let frame = $clipFrames[time];
        if (!frame)
            return;

        // Clear helper objects for previous frame
        // frameHelpers.clear();

        setCamera(frame);
        setDepthFrame(frame)

        // render();
    }

    function onParametersChange(parameters) {

        sessionLog.log(LogActionType.ModeSwitch, {mode: parameters.mode.value});
        
        updateCanvasesAppearance(parameters.mode.value !== "view");
        render();

    }

    onDestroy(() => {
        console.log("Destroy application viewport => Dispose of all THREE.js objects.");
        animationController.reset();

        viewPlaneGeom.dispose();
        viewPlaneMat.dispose();

        $clipFrames.forEach((frame) => frame.dispose());

        if (videoTex)
            videoTex.dispose();

    })


    onMount(() => {
        svg = d3.select("svg");

        renderer = new THREE.WebGLRenderer({ canvas: threeDOMElement });
        renderer.setSize( window.innerWidth, window.innerHeight );
        // container.appendChild( renderer.domElement );

        composer = new EffectComposer( renderer );

        // Define scene and base elements
        scene = new THREE.Scene();
        scene.background = new THREE.Color(1, 1, 1);
        // scene.background = new THREE.Color(0xe0e0e0);

        // scene.add(frameHelpers);
        scene.add(canvasContainer);


        // const light = new THREE.AmbientLight( 0x404040 ); // soft white light
        // scene.add( light );
        // const directionalLight = new THREE.DirectionalLight( 0xffffff, 0.5 );
        // scene.add( directionalLight );

        // scene.add( new THREE.HemisphereLight( 0xffffff, 0x808080, 0.7 ) );


        // Set up cameras
        // views.forEach((view) => {
        // Values will be reset for the view aligned camera later
        let camera = new THREE.PerspectiveCamera(
            75,    // fov
            2,     // aspect (this will be updated by resizeRenderToDisplay to match the canvas size anyway)
            0.01,   // near
            100.0   // far
        );
        // view.camera = camera;
        
        camera.layers.enable(0);

        const renderPass = new RenderPass( scene, camera );
        composer.addPass( renderPass );

        // Post-processing passes
        // thickenStrokePostProcessingPass = new ThickenStrokesPass(new THREE.Vector2(window.innerWidth, window.innerHeight), scene, camera);
        // composer.addPass(thickenStrokePostProcessingPass);

        // depthVisPass = new VisualizeDepthPass(new THREE.Vector2(window.innerWidth, window.innerHeight), scene, camera);
        // composer.addPass(depthVisPass);

        aaPass = new ShaderPass( FXAAShader );
        composer.addPass(aaPass);


        // View aligned plane (for the frames and depth maps)
        viewPlaneGeom = new THREE.BufferGeometry();

        let z = -1.0;
        viewPlaneGeom.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array([   -1,-1,z, 1,-1,z, 1,1,z, -1, -1, z, 1, 1, z, -1, 1, z]), 3 ) );

        viewPlaneMat = new THREE.ShaderMaterial({
            uniforms :{
                // resolution: { value: new THREE.Vector2( window.innerWidth, window.innerHeight ) },
                // viewOffset: { value: new THREE.Vector2( 0, 0 ) },
                tex: { value: undefined },
                depthTex: { value: undefined },
                opacity: { value: 1.0 },
                depthRange: { value: 1.0 },
                depthOffset: { value: 0.0},
                nearPlane: { value: 0.1 },
                farPlane: { value: 10.0 }
            },
            vertexShader : vertexShader,
            fragmentShader : fragmentShader,
            transparent: true,
            side: THREE.DoubleSide
        });


        const viewPlane = new THREE.Mesh( viewPlaneGeom, viewPlaneMat );

        viewPlane.renderOrder = 0;

        // This is essential, otherwise the plane will sometimes get culled!
        viewPlane.frustumCulled = false;


        // let colorTex = new THREE.VideoTexture( colorVideo );
        // viewPlaneMat.uniforms.tex.value = videoTex;
        // console.log(colorVideo);

        // let depthTex = new THREE.VideoTexture( depthVideo );
        // viewPlaneMat.uniforms.depthTex.value = depthVideo;

        scene.add( viewPlane );

        viewportImage = new THREE.WebGLRenderTarget(window.innerWidth, window.innerHeight, {
            depthBuffer: false,
            stencilBuffer: false,
        });


        // if (saveToLoad.data !== undefined) {
        //     animationController.loadExportedScene(saveToLoad.data)
        // }

        render();

        initialiseExporter(scene);
    });

    function onVideoLoad() {
        viewPlaneMat.uniforms.tex.value = videoTex;
        viewPlaneMat.needsUpdate = true;
        dimensionsNeedUpdate = true;
        // resizeCanvasToDisplaySize();

        if (saveToLoad.data !== undefined) {
            animationController.loadExportedScene(saveToLoad.data);
            saveToLoad.data = undefined;
        }

        setExporterResolution(videoTex);
    }

    function setCamera(frame) {
        // Set camera for every pass
        composer.passes.forEach((pass) => {
            pass.camera = frame.camera;
        })

        // Update depth parameters
        viewPlaneMat.uniforms.depthOffset.value = +frame.cameraData['depthOffset'];
        viewPlaneMat.uniforms.depthRange.value = +frame.cameraData['depthRange'];

        const { near, far } = frame.getNearFar();

        // console.log("near far " + near + " " + far);


        viewPlaneMat.uniforms.nearPlane.value = near;
        viewPlaneMat.uniforms.farPlane.value = far;

        viewPlaneMat.needsUpdate = true;
        
    }

    function setDepthFrame(frame) {
        viewPlaneMat.uniforms.depthTex.value = frame.depth;
        viewPlaneMat.needsUpdate = true;
    }

    function resizeCanvasToDisplaySize() {
        let parentWidth = viewportWidth;
        let parentHeight = viewportHeight;

        if (!dimensionsNeedUpdate)
            return;

        if (!renderer || !viewportContainer)
            return;

        if ($clipFrames.length < 1)
            return;

        if (!videoTex)
            return;

        console.log("resizing");

        const canvas = renderer.domElement;

        let containerStyle = getComputedStyle(viewportContainer);
        let paddingHeight = parseFloat(containerStyle.paddingTop) + parseFloat(containerStyle.paddingBottom);
        let paddingWidth = parseFloat(containerStyle.paddingLeft) + parseFloat(containerStyle.paddingRight);

        parentWidth -= paddingWidth;
        parentHeight -= paddingHeight;

        // adjust renderer size to fit in parent
        let newHeight = canvas.height;
        let newWidth = canvas.width;

        let videoWidth = videoTex.source.data.videoWidth;
        let videoHeight = videoTex.source.data.videoHeight;

        let videoAspect = (videoHeight == 0) ? 1 : videoWidth / videoHeight;

        if (videoWidth > parentWidth) {
            newHeight = parentWidth / videoAspect;
            newWidth = parentWidth;
        }
        else {
            newWidth = videoWidth;
            newHeight = videoHeight;
        }

        if (newHeight > parentHeight) {
            newHeight = parentHeight;
            newWidth = parentHeight * videoAspect;
        }

        if (newWidth !== undefined && newWidth !== NaN) {
            renderer.setSize(newWidth, newHeight, true);
            composer.setSize(newWidth, newHeight);
            // thickenStrokePostProcessingPass.setSize(newWidth, newHeight);
            // depthVisPass.setSize(newWidth, newHeight);
            
            viewportImage.setSize(newWidth, newHeight);
            // viewportImage.width = newWidth;
            // viewportImage.height = newHeight;
        }

        aaPass.material.uniforms[ 'resolution' ].value.x = 1 / newWidth;
        aaPass.material.uniforms[ 'resolution' ].value.y = 1 / newHeight;

        // viewPlaneMat.uniforms.resolution.value = new THREE.Vector2(canvas.width, canvas.height);


        // Change resolution of gizmos overlay
        svg.attr("viewBox", "0 0 " + canvas.width + " " + canvas.height);
        svg.attr("width", canvas.width);
        svg.attr("height", canvas.height);

        dimensionsNeedUpdate = false;

        render();


    }


    function render() {
        // requestAnimationFrame( render );

        if (!renderer)
            return;

        if (!videoTex)
            return;

        // Do not render yet if time sync is not effective
        if (loadedVideoFrame !== $time)
            return;

        const frame = $clipFrames[$time];

        if (frame && frame.camera) {
            const t0 = performance.now();

            composer.render();

            const t1 = performance.now();
            console.log(`Rendering took ${t1 - t0} milliseconds.`);

            console.log("rendering from viewport");

            dispatch('rendered');

            if (renderingFramesForExport) {
                viewPlaneMat.needsUpdate = true;
                viewPlaneMat.uniforms.tex.value.needsUpdate = true;
                exportNextFrame();
            }

        }

    }

    afterUpdate(() => {
        resizeCanvasToDisplaySize();
        drawGizmos();
        // render();
    })

</script>

<style>
    .scene-container {
        background-color: rgb(37, 37, 37);
        flex-grow: 4;
        padding: 20px;
        display: flex;
        flex-direction: column;
        min-width: 0;
    }

    .overlay {
        z-index: 10;
        min-width: 0;
    }

    canvas, svg {
        position: absolute;
        top: 0;
        left: 0;
    }

    #three-scene {
        z-index: 0;
    }

    .hidden {
        visibility: hidden;
    }

    :global(.crosshair) {
        fill: white;
        filter: drop-shadow(2px 2px 2px rgb(37, 37, 37))
        /* stroke: gray; */
        /* stroke-width: 5px; */
    }

    :global(.gauge) {
        fill: white;
    }

    :global(.draggable > .crosshair, .draggable.gauge) {
        fill:#4EB2DD;
        /* stroke-opacity: 1; */
    }

    :global(.draggable) {
        cursor: move;
    }

    /* :global(.has-keyframe > .crosshair, .draggable.has-keyframe > .crosshair, .gauge.has-keyframe , .gauge.draggable.has-keyframe) { */
    :global(.draggable.has-keyframe > .crosshair, .gauge.draggable.has-keyframe) {
        fill:#8edd4e;
    }

    :global(svg.arrow) {
        stroke: white;
        stroke-width: 6;
        stroke-linecap: round;
        filter: drop-shadow(2px 2px 2px rgb(37, 37, 37))
    }

    :global(svg.loading, .gauge.loading) {
        cursor: wait;
    }

    :global(.loading > .crosshair, .gauge.loading) {
        fill: rgb(37, 37, 37);
    }


</style>


<div class="scene-container" bind:this={viewportContainer} bind:offsetWidth={viewportWidth} bind:offsetHeight={viewportHeight}>
    <div style="position: relative;">
        <canvas id="three-scene" bind:this={threeDOMElement}></canvas>
        <svg xmlns="http://www.w3.org/2000/svg"
            class="overlay"
            viewBox="0 0 30 20"
            id="ui-overlay"
            class:hidden={parameters.mode.value === "view"}>
        </svg>
    </div>
</div>

<VideoManager 
    bind:tex={videoTex} 
    bind:videoFrame={loadedVideoFrame} 
    on:update={render} 
    on:load={onVideoLoad}/>


<ResultExporter 
    active={parameters.mode.value === "view"}
    bind:triggerExport={triggerExport}
    bind:renderingFrames={renderingFramesForExport}
    bind:setResolution={setExporterResolution} 
    bind:exportFrame={exportNextFrame} 
    bind:onSceneInitialisation={initialiseExporter} />