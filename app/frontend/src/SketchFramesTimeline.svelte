<script>
    import {onMount, afterUpdate} from 'svelte';
    import * as d3 from "d3";

    import Button from './components/Button.svelte';
    import VectorInput from "./components/VectorInput.svelte";
    import DropdownSelect from "./components/DropdownSelect.svelte";

    import { animationController } from './AnimationController.js';

    import { time, clipFrames, dialogProps } from './store.js';
    import Parameter from './components/Parameter.svelte';
    import IconButton from './components/IconButton.svelte';

    let { selectedCanvas } = animationController;


    let frames = [];
    let clipParameters = {
        "Frame Duration": 1,
        "Start Frame": 1,
        "End Frame": undefined,
    }
    let clipMode = "";
    let paddingMode = "";

    let currentActiveFrameIdx = -1;

    let hovering = -1;

    let thumbnailsNeedUpdate = true;


    $: $selectedCanvas, setCanvas();
    $: $time, $selectedCanvas, updateActiveFrame();

    export let svgTransform;

    function updateActiveFrame() {
        if ($selectedCanvas) {
            currentActiveFrameIdx = $selectedCanvas.animationClip.getAnimationFrameIndexAt($time);
        }
    }
    
    function setCanvas() {
        // console.log("update frames")
        if ($selectedCanvas) {
            frames = $selectedCanvas.animationClip.frames;

            clipParameters["Frame Duration"] = $selectedCanvas.animationClip.frameDuration;
            clipParameters["Start Frame"] = $selectedCanvas.animationClip.startTime + 1;
            clipParameters["End Frame"] = $selectedCanvas.animationClip.endTime ? $selectedCanvas.animationClip.endTime + 1 : $clipFrames.length;

            clipMode = $selectedCanvas.animationClip.mode;
            paddingMode = $selectedCanvas.animationClip.padding;

            // drawThumbnails();
            thumbnailsNeedUpdate = true;
        }
        else
            frames = [];
    }


    function addFrame() {
        if ($selectedCanvas) {
            const newFrameIdx = $selectedCanvas.addFrame($time);
            animationController.updateCanvases();
            // console.log(newFrameIdx)
            goToFrame(newFrameIdx);
        }
    }

    function deleteFrame(frameIdx) {
        dialogProps.set(
            {
                active: true,
                title: `Delete frame ${frameIdx}?`,
                message: "",
                onCancel: () => {},
                onOkay: () => { 
                    $selectedCanvas.animationClip.deleteFrame(frameIdx);
                    animationController.updateCanvases();
                 }
            }
        )

    }

    function goToFrame(frameIdx) {
        // let dt = frameIdx - currentActiveFrameIdx;
        const newTime = $selectedCanvas.animationClip.getNearestTimeForFrame($time, frameIdx);
        time.update((t) => Math.max(0, Math.min(newTime, $clipFrames.length - 1)));
    }

    function updateClipParameters() {
        $selectedCanvas.animationClip.setParameters(clipParameters["Start Frame"] - 1, clipParameters["End Frame"] - 1, clipParameters["Frame Duration"]);
        $selectedCanvas.animationClip.setMode(clipMode);
        $selectedCanvas.animationClip.setPadding(paddingMode);
        animationController.updateCanvases();
        $selectedCanvas.updateStrokes($time);
    }

    afterUpdate(() => {
        if (thumbnailsNeedUpdate)
            drawThumbnails();
    })

    function drawThumbnails() {
        if ($selectedCanvas) {
            // Draw the frames in each canvas
            frames.forEach((frame, idx) => {
                // Get canvas context
                // const ctx = document.getElementById("frame-canvas-" + idx).getContext( '2d' );
                // ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
                let svg = d3.select(`svg#frame-canvas-${idx}`)
                svg.selectAll("path").remove();
                $selectedCanvas.animationClip.renderStrokesAtFrame(idx, svg, false);
            })

            thumbnailsNeedUpdate = false;
        }
    }

    function changeFrameIdx(start, target) {
        console.log("changing frame idx from " + start + " to " + target);
        $selectedCanvas.animationClip.changeFrameIdx(start, target);
        hovering = -1;

        // updateFrames();
        drawThumbnails();

        // Set the time so that the dropped frame is still selected
        goToFrame(target);
    }

    // Drag and drop repositioning
    const drop = (event, target) => {
        event.dataTransfer.dropEffect = 'move'; 
        const start = parseInt(event.dataTransfer.getData("text/plain"));
        if (start < target) {
            // If we put a frame later in time, we need to 
            target -= 1;
        }
        changeFrameIdx(start, target);
        // console.log("changing frame idx from " + start + " to " + target);
        // $selectedCanvas.animationClip.changeFrameIdx(start, target);
        // hovering = -1;

        // // updateFrames();
        // drawThumbnails();

        // // Set the time so that the dropped frame is still selected
        // goToFrame(target);

    }

    const dragStart = (event, i) => {
        goToFrame(i);
        console.log("dragging");
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.dropEffect = 'move';
        const start = i;
        event.dataTransfer.setData('text/plain', start);
    }

</script>

<style>

    .container {
        padding-top: 5px;
    }

    .frames-editor {
        display: flex;
        justify-content: space-between;
        flex-direction: row;
    }

    .frames-navigator {
        display: flex;
        /* gap: 5px; */
        flex-direction: row;
        overflow-x: auto;
        max-width: 100%;
        margin-right: 5px;
    }

    svg {
        border: 5px solid white;
        background-color: white;
    }

    svg.active {
        border: 5px solid #8edd4e;
    }

    @keyframes entering {
        from {
            background-color: inherit;
            width: 5px;
        }
        to {
            background-color: #4EB2DD;
            width: 15px;
        }
    }

    @keyframes exiting {
        from {
            background-color: #4EB2DD;
            width: 15px;
        }
        to {
            background-color: inherit;
            width: 5px;
        }
    }

    .frame-miniature {
        position: relative;
    }

    .delete-button {
        position: absolute;
        top: 0px;
        right: 0px;
        margin: 2px;
        width: 10px;
        height: 10px;
        background: mediumvioletred;
    }

    .between-frames {
        width: 5px;
        background-color: inherit;
        flex-shrink: 0;
        /* animation-name: exiting;
        animation-duration: 0.5s; */
    }

    .between-frames.is-active {
        background-color: #4EB2DD;
        width: 15px;
        animation-name: entering;
        animation-duration: 0.5s;
    }

    .clip-modes {
        display: flex;
        flex-direction: row;
        gap: 5px;
    }

</style>

<svelte:window
        drawThumbnails();
    on:keydown={(e) => {if (e.code == "ArrowLeft") { e.preventDefault();  if ($selectedCanvas) changeFrameIdx(currentActiveFrameIdx, Math.max(0, currentActiveFrameIdx - 1)); }} } 
    on:keydown={(e) => {if (e.code == "ArrowRight") { e.preventDefault(); if ($selectedCanvas) changeFrameIdx(currentActiveFrameIdx, Math.min($selectedCanvas.animationClip.N - 1, currentActiveFrameIdx + 1)); }} } 
/>

{#if $selectedCanvas}

<div class="container">
    <div class="frames-editor">
        <div class="frames-navigator">
            
            {#each frames as frame, i (i)}

                {#if i == 0}
                    <div class="between-frames" 
                        ondragover="return false" 
                        on:drop|preventDefault={event => drop(event, hovering)}
                        on:dragenter={() => {hovering = i;}} 
                        on:dragleave={() => hovering = -1}
                        class:is-active={hovering === i}></div>
                {/if}

                <!-- <canvas 
                    width="50" height="50" 
                    id="frame-canvas-{i}" 
                    class:active={i === currentActiveFrameIdx}
                    on:click={() => goToFrame(i)}
                    draggable={true}
                    on:dragstart={event => dragStart(event, i)}
                >
                </canvas> -->
                <div
                    class="frame-miniature"
                    draggable={true}
                    on:dragstart={event => dragStart(event, i)}
                >
                    <svg xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 50 50"
                        class="overlay"
                        width="50" height="50" 
                        id="frame-canvas-{i}" 
                        class:active={i === currentActiveFrameIdx}
                        on:click={() => goToFrame(i)}
                        style={svgTransform}
                        >
                    </svg>
                    <div class="delete-button" hidden={i !== currentActiveFrameIdx || $selectedCanvas.animationClip.frames.length < 2}>
                        <IconButton on:click={() => deleteFrame(i)}>
                        </IconButton>
                    </div>
                </div>


                {#if i < frames.length}
                    <div class="between-frames" 
                        ondragover="return false" 
                        on:drop|preventDefault={event => drop(event, hovering)}
                        on:dragenter={() => {hovering = i + 1;}} 
                        on:dragleave={() => hovering = -1}
                        class:is-active={hovering === i + 1}></div>
                {/if}

            {/each}
        </div>

        <div style="display: flex; height: 40px;">
            <Button on:click={addFrame}> Add </Button>
        </div>

    </div>
    <div class="clip-properties">
        <div class="clip-modes">
            <Parameter label="Mode">
                <DropdownSelect bind:value={clipMode} options={["once", "loop"]} on:change={() => updateClipParameters()}/>
            </Parameter>
            <Parameter label="Padding">
                <DropdownSelect bind:value={paddingMode} options={["hide", "clamp"]} on:change={() => updateClipParameters()}/>
            </Parameter>
        </div>
        <Parameter label="Timing">
            <VectorInput bind:values={clipParameters} labels={["Frame Duration", "Start Frame", "End Frame"]} on:change={ () => updateClipParameters() } min=1 max={$clipFrames.length} step = 1/>
        </Parameter>
    </div>
</div>
{/if}
