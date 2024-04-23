

<script>
    import {onMount, afterUpdate} from 'svelte';
    import { Vector2, Color, Vector3 } from 'three';
    import * as d3 from "d3";

    import ToggleSelect from "./components/ToggleSelect.svelte";
    import Slider from "./components/Slider.svelte";
    import ColorPicker from "./components/ColorPicker.svelte";
    import Parameter from './components/Parameter.svelte';
    import Button from './components/Button.svelte';

    import SceneViewFromCanvas from './SceneViewFromCanvas.svelte';
    import SketchFramesTimeline from './SketchFramesTimeline.svelte';


    import { animationController } from './AnimationController.js';

    import { time, clipFrames } from './store.js';

    import { LogActionType, sessionLog } from './SessionLog.js';


    const eps = 0.01;

    let { selectedCanvas } = animationController;

    // export let drawingCanvas;
    export let drawTools;
    export let viewportImage;
    export let canvasDim;

    export let triggerRender;

    let drawingCanvas;
    let drawingContext;
    let cursor;

    let strokesSvg;

    let canvasTransform;
    let svgTransform;

    let viewQuality = "good";
    // let minProjectedDim;
    let skewness;

    // let canvasRawDimension = 1000;

    let width = 300;
    // let height = 300;


    let painting = false;
    const drawStartPos = new Vector2();

    let currentStrokeID = -1;

    $: $selectedCanvas, renderStrokes();
    $: $selectedCanvas, $time, updateOrientation();
    $: drawTools, onRadiusChange();
    $: drawTools, renderStrokes();

    $: viewQuality = (skewness < 0.6) ? "good" : (skewness < 0.9) ? "medium" : "poor";


    onMount(() => {
        drawingContext = drawingCanvas.getContext( '2d' );

        strokesSvg = d3.select("svg#drawing-canvas-strokes-overlay");

        renderStrokes();

    });


    function onRadiusChange() {
        if (cursor !== undefined) {
            cursor.style.width = drawTools.width + "px";
            cursor.style.height = drawTools.width + "px";
        }
    }

    function canvasToNDC(x, y) {
        const {reverseX, reverseY} = $selectedCanvas.getProjectedOrientation($time);
        // console.log("x reversed? " + reverseX)
        // console.log("y reversed? " + reverseY)
        y = canvasDim - y;
        let ndcX = (x / canvasDim) * 2 - 1;
        let ndcY = (y / canvasDim) * 2 - 1;
        if (reverseY)
            ndcY *= -1;
        if (reverseX)
            ndcX *= -1;
        return new Vector2(ndcX, ndcY);
    }

    function getNDCToolWidth() {
        return 0.5 * drawTools.width / canvasDim;
    }

    function start(e) {
        // Make sure that we are allowed to paint
        if (drawTools.mode !== "pencil" || !$selectedCanvas || $selectedCanvas.animationClip.getAnimationFrameIndexAt($time) === -1)
            return;


        painting = true;
        drawStartPos.set( e.offsetX, e.offsetY );

        currentStrokeID = $selectedCanvas.createStroke($time);

        $selectedCanvas.setStrokeColor($time, currentStrokeID, new Color(drawTools.color))
        $selectedCanvas.setStrokeRadius($time, currentStrokeID, getNDCToolWidth());
    }

    function enter(e) {
        cursor.style.visibility = "visible";
    }

    function draw(e) {
        // Move pointer
        cursor.style.left = e.clientX + "px",
        cursor.style.top = e.clientY + "px";

        if ( painting && drawingContext ) {
            let x = e.offsetX;
            let y = e.offsetY;

            // Prevent drawing super short segments
            if (Math.pow(x - drawStartPos.x, 2) + Math.pow(y - drawStartPos.y, 2) < Math.pow(eps * canvasDim, 2)) {
                // console.log("prevent short segment")
                return;
            }

            drawingContext.beginPath();

            if(drawTools.mode=='pencil') {
                drawingContext.globalCompositeOperation = 'source-over';
                drawingContext.lineWidth = drawTools.width;
                drawingContext.strokeStyle = drawTools.color;
            }
            else {
                console.log("erasing")
                drawingContext.globalCompositeOperation = 'destination-out';
                drawingContext.strokeStyle = 'rgba(0,0,0,1.0)';
                drawingContext.lineWidth = drawTools.width;
            }

            drawingContext.moveTo( drawStartPos.x, drawStartPos.y );
            drawingContext.lineCap = 'round';
            drawingContext.lineTo( x, y );
            drawingContext.stroke();

            $selectedCanvas.addPointsToStroke($time, currentStrokeID, [ canvasToNDC(drawStartPos.x, drawStartPos.y) , canvasToNDC(x, y)] );
            // animationController.updateCanvases();
            drawStartPos.set( x, y );


        }
    }

    function stop(e) {

        if (painting) {
            sessionLog.log(LogActionType.StrokeCreate, {strokeID: currentStrokeID, canvasID: $selectedCanvas.ID});
            currentStrokeID = -1;

            animationController.updateCanvases();
            // renderStrokes();
            // Clear drawing pad (the stroke is now rendered in the scene)
            drawingContext.clearRect( 0, 0, drawingCanvas.width, drawingCanvas.height);
        }
        else {
            cursor.style.visibility = "hidden";
        }

        painting = false;

    }

    function renderStrokes() {
        if (strokesSvg && $selectedCanvas) {
            strokesSvg.selectAll("path").remove();
            // In edit mode, render interactable strokes:
            if (drawTools.mode === "edit")
                $selectedCanvas.renderStrokes($time, strokesSvg);
            else if (drawTools.mode === "pencil") {
                // In draw mode, do onion skinning
                // console.log("onion")
                $selectedCanvas.renderOnionSkinning($time, strokesSvg);

            }
        }
    }

    function updateOrientation() {
        if ($selectedCanvas !== undefined) {
            // const canvasNormal = $selectedCanvas.getNormal($time);
            // const viewDir = $clipFrames[$time].getViewDirection();
            // console.log(canvasNormal);
            // console.log(viewDir);

            // console.log("quality ?")
            // viewQuality = viewDir.dot(new Vector3(canvasNormal.x, canvasNormal.y, canvasNormal.z));

            const {reverseX, reverseY} = $selectedCanvas.getProjectedOrientation($time);

            let elements = [1, 0, 0, 1, 0, 0];
            let svgElements = [1, 0, 0, 1, 0, 0];
            if (reverseX) {
                elements[0] = -1;
                svgElements[0] = -1;
            }
            if (reverseY) {
                elements[3] = -1;
                svgElements[3] = 1;
            }
            else {
                svgElements[3] = -1;
            }

            canvasTransform = "transform: matrix(";
            elements.forEach((e, idx) =>  {
                canvasTransform += e;
                if (idx < 5) canvasTransform += ",";
            });

            svgTransform = "transform: matrix(";
            svgElements.forEach((e, idx) =>  {
                svgTransform += e;
                if (idx < 5) svgTransform += ",";
            });
            
            canvasTransform += ");"
            svgTransform += ");"
        }
    }


    onMount(() => {
        onRadiusChange();
    })


</script>

<style>
    .sketching-panel {
        /* width: 25%; */
        /* max-width: 400px; */
        display: flex;
        flex-grow: 1; 
        flex-direction: column; 
        /* flex-grow: 1;  */
        background-color: rgb(37, 37, 37);
        padding: 20px;
        overflow-y: auto;
        overflow-x: clip;
    }


    .canvas-container {
        /* background-color: rgb(37, 37, 37); */
        /* flex: auto; */
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        /* min-width: 0; */
        /* max-width: 30%; */
    }

    .canvas-background {
        background-color: white;
        transform-origin: top left;
    }

    .hidden {
        visibility: hidden;
    }

    .cursor {
        position: fixed;
        border-radius: 50%;
        transform: translateX(-50%) translateY(-50%);
        pointer-events: none;
        left: -100px;
        top: 50%;
        background-color: transparent;
        z-index: 10000;
        border: 1px solid rgb(77, 77, 77);
        height: 30px;
        width: 30px;
    }

    .overlay {
        position: absolute;
        top: 0;
        left: 0;
        z-index: 1;
    }

    .on-top {
        z-index: 10;
    }

    #drawing-canvas {
        opacity: 0.8;
        cursor: crosshair;
    }

    .hidden {
        visibility: hidden;
    }

    .semi-transparent {
        opacity: 0.2;
    }

    #drawing-canvas.forbidden {
        background-color: black;
        opacity: 0.7;
        cursor: not-allowed;
    }

    :global(.depth-gizmo) {
        cursor: pointer;
        /* fill: white; */
    }

    .view-quality-indicator {
        font-size: 0.8em;
        padding: 5px;
    }

    .view-quality-indicator.good {
        background-color: rgb(99, 183, 90);
    }

    .view-quality-indicator.medium {
        background-color: rgb(237, 189, 74);
    }

    .view-quality-indicator.poor {
        background-color: rgb(229, 57, 53);
    }

</style>



<div class="sketching-panel">
    <div class="canvas-container">
        <!-- <div class="toolbar">
        </div> -->
        {#if $selectedCanvas === undefined}
        <div class="warning">
            Please select a canvas by clicking on it.
        </div>
        {/if}
        <div class="view-quality-indicator" class:good={viewQuality === "good"} class:medium={viewQuality === "medium"} class:poor={viewQuality === "poor"}>
            View quality is {viewQuality}.
        </div>
        <div bind:clientWidth={width} style="height: {width}px">
            <div class="canvas-background" class:hidden={$selectedCanvas === undefined} style="transform: scale({width/canvasDim});">
                    <canvas
                        id="drawing-canvas"
                        class="overlay"
                        width={canvasDim} 
                        height={canvasDim}
                        bind:this={drawingCanvas}
                        on:touchmove={(e) => {e.preventDefault();}}
                        on:pointerdown={start}
                        on:pointermove={draw}
                        on:pointerleave={stop}
                        on:pointerup={stop}
                        on:pointerenter={enter}
                        class:on-top={drawTools.mode === "pencil"}
                        class:forbidden={$selectedCanvas && $selectedCanvas.animationClip.getAnimationFrameIndexAt($time) === -1}
                        >
                    </canvas>
                    <svg xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 {canvasDim} {canvasDim}"
                        width={canvasDim} height={canvasDim}
                        id="drawing-canvas-strokes-overlay"
                        class="overlay"
                        class:on-top={drawTools.mode === "edit"}
                        class:semi-transparent={drawTools.mode === "pencil"}
                        style={svgTransform}>
                    </svg>
                    <SceneViewFromCanvas 
                        bind:skewness={skewness}
                        bind:triggerRender={triggerRender}
                        viewportImage={viewportImage} 
                        width={canvasDim} height={canvasDim} 
                        style={canvasTransform}/>
            </div>
        </div>
        <div class='cursor' id="cursor" bind:this={cursor}></div>
    </div>
    {#if $selectedCanvas}
        <SketchFramesTimeline svgTransform={svgTransform}/>
    {/if}

</div>
<!-- <canvas id="hidden-canvas" width={canvasDim} height={canvasDim} bind:this={hiddenCanvas}>

</canvas> -->