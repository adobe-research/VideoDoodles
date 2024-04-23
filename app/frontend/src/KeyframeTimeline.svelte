<script>
    import * as d3 from "d3";
    import {onMount, afterUpdate} from 'svelte';

    import Button from "./components/Button.svelte";

    import { animationController } from "./AnimationController.js";
    import { clipFrames, time, dialogProps } from "./store.js";
    import IconButton from "./components/IconButton.svelte";
    import { LogActionType, sessionLog } from "./SessionLog";

    // export let currentFrameId = 0;

    let { animatedCanvases } = animationController;

    export let uneditable;
    export let viewportImage;
    export let drawMode;

    // Element dimensions
    let timelineWidth = 100;
    let height = 30;

    let timelineHorizontalPadding = height * 0.5;

    let keyframeSize = height * 0.3;
    let trajectorySize = height * 0.2;
    let trajectoryPointSize = height * 0.1;
    let timeTickWidth = 2;

    $: $time, updateTimeTick();


    function getUnitDistance() {
        return (timelineWidth - timelineHorizontalPadding) / $clipFrames.length;
    }

    function getUnitTime() {
        return $clipFrames.length / (timelineWidth - timelineHorizontalPadding);
    }

    function timeToX(time, alignRight=false) {
        let x = Math.floor(timelineHorizontalPadding + time * getUnitDistance());
        if (alignRight)
            x -= getUnitDistance() * 0.5;
        return x;
    }

    function drawTimelines() {
        console.log("redrawing timelines");
        const t0 = performance.now();

        const totalFrames = $clipFrames.length;

        if ($animatedCanvases === undefined)
            return;
        
        Object.values($animatedCanvases).forEach((c, idx) => {
            let timelineSVG = d3.select("#canvas-" + c.ID + " svg");

            if (timelineSVG.empty() ) {
                timelineSVG = d3.select("#canvas-" + c.ID)
                    .append("svg")
                    .attr("width", timelineWidth)
                    .attr("height", height);
            }

            timelineSVG
                .classed("selected", c.gizmo.selected)
                .attr("width", timelineWidth)
                .on("click", (e) => {
                    let x = e.layerX - timelineHorizontalPadding;
                    let newTime = x * getUnitTime();
                    time.update((t) => Math.max(0, Math.min(Math.round(newTime), totalFrames - 1)));

                    sessionLog.log(LogActionType.NavigateTime, {time: $time, type: "click"})
                });

            // Draw trajectory points (to show solved status)
            if (c.gizmo.selected) {
                timelineSVG.selectAll(".trajectory-points")
                    .data(c.trajectory)
                    .enter()
                    .append("circle")
                    .classed("trajectory-points", true);

                let trajPtRadius = Math.min(timelineSVG.attr("height") * 0.3,  getUnitDistance() * 0.2);
                
                timelineSVG.selectAll(".trajectory-points")
                    .attr("r", trajPtRadius)
                    .attr("cx", (pt, idx) => timeToX(idx))
                    .attr("cy", timelineSVG.attr("height") * 0.5)
                    .style("fill", (pt, idx) => {
                        if (!drawMode) {
                            return pt.positionSolved ? (pt.rotationSolved ? "#4288a6" : "#86c5e0") : "#ffffff";
                        }
                        else {
                            // Draw color depending on projected skewness
                            let skewness =c.getProjectedSkewness(idx, viewportImage.width, viewportImage.height);
                            return (skewness < 0.6) ? "rgb(99, 183, 90)" : (skewness < 0.9) ? "rgb(237, 189, 74)" : "rgb(229, 57, 53)";
                        }
                    });

                timelineSVG.selectAll(".trajectory-points")
                    .exit().remove();

            }
            else {
                timelineSVG.selectAll(".trajectory-points").remove();
            }


            // Draw trajectory segments, if there are any keyframes
            // timelineSVG.selectAll(".segment").remove();
            // if (Object.keys(c.keyframes).length > 0) {
            //     Object.values(c.positionSegments).forEach((s) => {
            //         if (s.end - s.start > 1) {
            //             const xStart = timeToX(s.start + 1);
            //             const xEnd = timeToX(s.end - 1);
            //             timelineSVG.append("rect")
            //                 .classed("segment", true)
            //                 .attr("fill", "yellow")
            //                 .attr("x", xStart)
            //                 .attr("y", timelineSVG.attr("height") * 0.5 - trajectorySize)
            //                 // .attr("rx", trajectorySize * 0.5)
            //                 .attr("width", xEnd - xStart)
            //                 .attr("height", trajectorySize);
            //         }
            //     });

            //     Object.values(c.orientationSegments).forEach((s) => {
            //         if (s.end - s.start > 1) {
            //             const xStart = timeToX(s.start + 1);
            //             const xEnd = timeToX(s.end - 1);
            //             timelineSVG.append("rect")
            //                 .classed("segment", true)
            //                 .attr("fill", "red")
            //                 .attr("x", xStart)
            //                 .attr("y", timelineSVG.attr("height") * 0.5)
            //                 // .attr("rx", trajectorySize * 0.5)
            //                 .attr("width", xEnd - xStart)
            //                 .attr("height", trajectorySize);
            //         }
            //     });
            // }


            // Draw time tick
            let timeTick = timelineSVG.select(".time-tick");
            if (timeTick.empty()) {
                timelineSVG.append("rect")
                    .classed("time-tick", true)
            }

            timeTick                    
                .attr("y", 0)
                .attr("height", height)
                .attr("x", timeToX($time, true))
                .attr("width", getUnitDistance())

            // Draw keyframes
            timelineSVG.selectAll(".keyframes").remove();

            let keyframeSize = Math.min(timelineSVG.attr("height") * 0.5,  getUnitDistance() * 0.4);

            Object.keys(c.keyframes).forEach((keyframeTime) => {
                const x = timeToX(keyframeTime);
                timelineSVG.append("rect")
                    .classed("keyframes", true)
                    .classed("empty", c.keyframes[keyframeTime].isEmpty())
                    .attr("x", x - keyframeSize * 0.5)
                    .attr("y", timelineSVG.attr("height") * 0.5 - keyframeSize * 0.5)
                    .attr("width", keyframeSize)
                    .attr("height", keyframeSize);
            });


        })

        const t1 = performance.now();
        console.log(`Redrawing timelines took ${t1 - t0} milliseconds.`);
        
    }

    function updateTimeTick() {
        const totalFrames = $clipFrames.length;
        const totalWidth = timelineWidth - timelineHorizontalPadding;
        // console.log("update time tick");
        d3.selectAll("rect.time-tick")
            .attr("x", Math.floor(timelineHorizontalPadding + totalWidth * $time / totalFrames) - getUnitDistance() * 0.5);
    }

    function tryDeleteCanvas(canvasID) {
        dialogProps.set(
            {
                active: true,
                title: `Delete canvas ${canvasID}?`,
                message: "",
                onCancel: () => {},
                onOkay: () => { animationController.deleteCanvas(canvasID); }
            }
        )

    }

    afterUpdate(() => {
        drawTimelines();
    });

</script>

<style>

    .container {
        background-color: rgb(37, 37, 37);
        flex: auto;
        padding: 20px;
        max-height: 20%;
        overflow: auto;
    }

    .timeline-rows {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 2px;
    }

    .single-row {
        display: flex;
        width: 100%;
        gap: 5px;
    }

    .title {
        width: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding-right: 10px;
        cursor: pointer;
    }

    .timeline {
        flex: 1;
        min-width: 0;
    }

    .dynamic .title {
        color: rgb(220, 121, 7);
    }

    .selected .title {
        font-weight: 800;
    }

    .hidden {
        visibility: hidden;
    }

    :global(.timeline svg) {
        background-color: rgb(133, 133, 133);
        border-radius: 5px;
    }


    :global(.timeline svg.selected) {
        background-color: rgb(215, 215, 215);
    }

    :global(.timeline .keyframes) {
        transform-box: fill-box;
        transform-origin: center;
        transform: rotate(45deg);
        fill: #8edd4e;
        stroke:#8edd4e;
        stroke-opacity: 1;
        stroke-width: 3px;
    }

    :global(.timeline .keyframes.empty) {
        fill: rgb(215, 215, 215);
        stroke-width: 3px;
    }

    :global(.timeline .time-tick) {
        fill: #565656;
    }


</style>
<!-- <div id="row0" ></div> -->
<div class='container'>
    <div class="timeline-rows">
        {#if $animatedCanvases !== undefined}
            {#each Object.values($animatedCanvases) as animatedCanvas }
            <div class="single-row" class:dynamic={animatedCanvas.type === "dynamic"} class:selected={animationController.selectedCanvasID === animatedCanvas.ID}>
                <div class="title" on:click={() => animationController.selectCanvas(animatedCanvas.ID)}>Canvas&nbsp;{animatedCanvas.ID}</div>
                <div class="timeline" id="canvas-{animatedCanvas.ID}" bind:clientWidth={timelineWidth}></div>
                <div class:hidden={uneditable || animationController.selectedCanvasID !== animatedCanvas.ID}>
                    <IconButton on:click={() => { tryDeleteCanvas(animatedCanvas.ID) }}>
                        <i class="material-icons">delete_forever</i>
                    </IconButton>
                </div>
            </div>
            {/each}
        {/if}
    </div>
    <div class:hidden={uneditable}>
        <Button on:click={() => { animationController.addCanvas(); }}>
            New canvas
        </Button>
    </div>
</div>