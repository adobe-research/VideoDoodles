<script>
    import { Euler, Vector3, Matrix4 } from 'three';
    import Parameter from "./components/Parameter.svelte";
    import Button from "./components/Button.svelte";
    import VectorInput from "./components/VectorInput.svelte";
    import Loading from "./Loading.svelte";

    import { animationController } from './AnimationController.js';

    let { selectedCanvas } = animationController;

    import { time, dialogProps } from './store.js';
    import DropdownSelect from './components/DropdownSelect.svelte';
    import ToggleSelect from './components/ToggleSelect.svelte';
    import { sessionLog, LogActionType } from "./SessionLog";



    // let pos = [0, 0];
    // let depth = [0];
    // let rot = [0, 0, 0];
    // let scale = [1];

    let values = {
        "x": 0,
        "y": 0,
        "depth": 0,
        "rot": {
            "rot X": 0,
            "rot Y": 0,
            "rot Z": 0,
        },
        "scale": 1,
        "type": "static",
        "positionInterpolation": 1,
        "orientationInterpolation": 1,
    }

    $: $selectedCanvas, setCanvas();

    function rotMatToAxisAngle(rotMat) {
        const e = new Euler();
        e.setFromRotationMatrix(rotMat);
        return e;
    }

    function axisAngleToRotMat(axisAngles) {
        const e = new Euler(...axisAngles);
        const rotMat = new Matrix4();
        rotMat.makeRotationFromEuler(e);
        return rotMat;
    }
    
    
    function setCanvas() {
        if ($selectedCanvas) {
            const canvasPos = $selectedCanvas.getProjectedPosition($time);
            // pos = [canvasPos.x, canvasPos.y];
            // depth = [scaleDepth($selectedCanvas.getDepth($time))];
            const rot = rotMatToAxisAngle($selectedCanvas.getRotation($time));
            // const rot = rotMatToAxisAngle($selectedCanvas.getProjectedRotation($time));

            values = {
                "x": canvasPos.x,
                "y": canvasPos.y,
                "depth": $selectedCanvas.getDepth($time),
                "rot": {
                    "rot X": rot.x,
                    "rot Y": rot.y,
                    "rot Z": rot.z,
                },
                "scale": $selectedCanvas.canvas.scale,
                "type": $selectedCanvas.type,
                "positionInterpolation": 1,
                "orientationInterpolation": 1,
            }

            if ($selectedCanvas.getPositionSegment($time)) {
                values.positionInterpolation = $selectedCanvas.getPositionSegment($time).mode;
            }

            if ($selectedCanvas.getOrientationSegment($time)) {
                values.orientationInterpolation = $selectedCanvas.getOrientationSegment($time).mode;
            }
        }
    }

    function keyframeCanvas(props) {
        if ($selectedCanvas && props.length > 0) {
            const kfProps = {};
            props.forEach((prop) => {
                let newValue = values[prop];
                if (prop === "depth") {
                    // newValue = descaleDepth(newValue);
                    // console.log("new depth " + newValue);

                    // Prevent keyframing depth without keyframing x and y
                    if (!$selectedCanvas.isKeyframed("x") && (!props.hasOwnProperty("x") || !props.hasOwnProperty("y"))) {
                        // Add keyframe x and y at current position
                        kfProps["x"] = values["x"];
                        kfProps["y"] = values["y"];
                    }
                }
                if (prop === "rot") {
                    newValue = axisAngleToRotMat([values["rot"]["rot X"], values["rot"]["rot Y"], values["rot"]["rot Z"]])
                }
                kfProps[prop] = newValue;
            });
            $selectedCanvas.addKeyframe($time, kfProps);

            if ($selectedCanvas.type === "static")
                $selectedCanvas.inferTrajectory();

            animationController.updateCanvases();

            sessionLog.log(LogActionType.KeyframeAdd, {
                canvasID: $selectedCanvas.ID,
                keyframeTime: $time,
                editedProps: Object.keys(kfProps),
                type: "values",
            }, false);

            // animationController.debugSetRotation($selectedCanvas.ID, axisAngleToRotMat(rot));
        }
    }

    function setScale() {
        sessionLog.log(LogActionType.CanvasSetScale, {canvasID: this.ID, scale: values["scale"]});
        $selectedCanvas.canvas.setScale(values["scale"]);
        animationController.updateCanvases();
        $selectedCanvas.setTime($time);
    }

    function toggleKeyframedProps(props) {
        if ($selectedCanvas && props.length > 0 && $selectedCanvas.trajectoryUpToDate) {
            // For each property, check if it is already keyframed
            // - If not, add a keyframe
            // - If yes, remove the property

            let toAdd = [];
            let toRemove = [];

            props.forEach((prop) => {
                if ($selectedCanvas.isKeyframed($time, prop)) {
                    // Remove the keyframed property
                    toRemove.push(prop);
                }
                else {
                    toAdd.push(prop);
                }
            });

            keyframeCanvas(toAdd);
            $selectedCanvas.removeKeyframeProps($time, toRemove);
            animationController.updateCanvases();
        }
    }


    function inferTrajectory() {
        $selectedCanvas.inferTrajectory(); 
        animationController.updateCanvases();
    }

    function exportKeyframes() {
        $selectedCanvas.exportKeyframes();
    }

    function toggleType() {
        animationController.toggleType();
    }
    
    function trySetCanvasType() {
        if ($selectedCanvas && $selectedCanvas.type !== values.type && values.type === "static") {
            dialogProps.set(
                {
                    active: true,
                    title: "Change canvas type",
                    message: `Do you want to change the type of Canvas ${$selectedCanvas.ID} from ${$selectedCanvas.type} to ${values.type} (with ${$selectedCanvas.getKeyframes().length} keyframes)? This will clear all your keyframes.`,
                    onCancel: () => {values.type = $selectedCanvas.type},
                    onOkay: () => {             
                        $selectedCanvas.setType(values.type);
                        animationController.updateCanvases(); 
                    }
                }
            )

        }
        else {
            $selectedCanvas.setType(values.type);
            animationController.updateCanvases(); 
        }
    }

</script>

<style>

    .title {
        font-weight: bold;
        display: flex;
        margin: 0;
        border-bottom: white 1px solid;
        padding-bottom: 10px;
        justify-content: space-between;
        font-size: 0.9em;
        align-items: baseline;
    }

    h5 {
        margin: 0;
        padding-bottom: 5px;
        margin-top: 10px;
    }

    .container {
        background-color: rgb(37, 37, 37);
        /* flex: auto; */
        padding: 10px;
        min-width: 240px;
        /* max-width: 20%; */
        flex-grow: 1;
        overflow: auto;
    }

    .section {
        border-bottom: white 1px dashed;
        padding: 8px 0;
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .section:last-of-type {
        border: 0px;
    }

    .prop {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .keyframe-icon {
        border: 1px #8edd4e solid;
        width: 10px;
        height: 10px;
        transform: rotate(45deg);
        /* margin: 10px; */
    }

    .keyframed {
        background-color: #8edd4e;
    }

    .hidden {
        visibility: hidden;
    }

    .loading {
        cursor: wait;
    }

</style>

<svelte:window
    on:keydown={(e) => {if (e.code == "ArrowUp") { e.preventDefault();  if ($selectedCanvas) values["depth"] = values["depth"] + 0.005; keyframeCanvas(["x", "y", "depth"] ); }} } 
    on:keydown={(e) => {if (e.code == "ArrowDown") { e.preventDefault(); if ($selectedCanvas) values["depth"] = values["depth"] - 0.005; keyframeCanvas(["x", "y", "depth"] ); }} } 
    on:keydown={(e) => {if (e.code == "Enter") { e.preventDefault();  inferTrajectory(); } }}
/>

<div class='container'>
    {#if $selectedCanvas}
        <div class="title">
            Canvas {$selectedCanvas.ID}
            <div class:hidden={!$selectedCanvas.hasDirtySegments && $selectedCanvas.trajectoryUpToDate}>
                <Button on:click={inferTrajectory} disabled={!$selectedCanvas.trajectoryUpToDate}>
                    Update
                    <span class:hidden={$selectedCanvas.trajectoryUpToDate}><Loading/></span>
                </Button>
            </div>
        </div>
        <div class:loading={!$selectedCanvas.trajectoryUpToDate}>
            <div class="section">
                <Parameter label="Motion">
                    <ToggleSelect bind:value={values.type} options={[{label: "Static", value:"static"}, {label: "Dynamic", value:"dynamic"}]} on:change={() => { trySetCanvasType() } }/>
                </Parameter>
                <VectorInput bind:values={values} labels={["scale"]} on:change={ setScale } min=0.1  max=20/>
            </div>
            <div class="section">
                <div class="prop">
                    <div class="keyframe-icon" 
                        class:keyframed={$selectedCanvas.isKeyframed($time, "x")}
                        on:click={() => toggleKeyframedProps(["x", "y"])}>
                    </div>
                    <VectorInput bind:values={values} labels={["x", "y"]} on:change={() => keyframeCanvas(["x", "y"])} step=0.005 min=0 max=1 disabled={ !$selectedCanvas.trajectoryUpToDate }/>
                </div>
                <div class="prop">
                    <div class="keyframe-icon" 
                        class:keyframed={$selectedCanvas.isKeyframed($time, "depth")}
                        on:click={() => toggleKeyframedProps(["depth"])}>
                    </div>
                    <VectorInput bind:values={values} labels={["depth"]} on:change={() => keyframeCanvas(["depth"])} step=0.005 disabled={ !$selectedCanvas.trajectoryUpToDate } />
                </div>
                <div class="prop">
                    <div class="keyframe-icon" 
                        class:keyframed={$selectedCanvas.isKeyframed($time, "rot")}
                        on:click={() => toggleKeyframedProps(["rot"])}>
                    </div>
                    <VectorInput bind:values={values["rot"]} labels={["rot X", "rot Y", "rot Z"]} on:change={ () => keyframeCanvas(["rot", "x", "y"]) }  disabled={ !$selectedCanvas.trajectoryUpToDate } />
                </div>
                <!-- <div class="prop">
                    <div class="keyframe-icon" 
                        class:keyframed={$selectedCanvas.isKeyframed($time, "scale")}
                        on:click={() => toggleKeyframedProps(["scale"])}>
                    </div>
                    <VectorInput bind:values={values} labels={["scale"]} on:change={ () => keyframeCanvas(["scale"]) } min=0.1  max=10/>
                </div> -->
            </div>
            <!-- We don't allow multiple interpolation modes for a static canvas. -->
            <div class="section" class:hidden={$selectedCanvas.type === "static"}>
                <div class:hidden={!$selectedCanvas.getPositionSegment($time)}>
                    <h5>Position. Frames: {$selectedCanvas.getPositionSegment($time) ? $selectedCanvas.getPositionSegment($time).toString() : ""}</h5>
                    <Parameter label="Interpolation">
                        <ToggleSelect 
                            bind:value={values.positionInterpolation} 
                            options={[{label: "Tracking", value: 1}, {label: "Linear", value: 0}]}
                            on:change={() => {
                                if (values.positionInterpolation === 0)
                                    $selectedCanvas.getPositionSegment($time).setLinear();
                                if (values.positionInterpolation === 1)
                                    $selectedCanvas.getPositionSegment($time).setTracking();
                                animationController.updateCanvases();
                            }}
                        />
                    </Parameter>
                </div>
                <div class:hidden={!$selectedCanvas.getOrientationSegment($time)}>
                    <h5>Orientation. Frames: {$selectedCanvas.getOrientationSegment($time) ? $selectedCanvas.getOrientationSegment($time).toString(): ""}</h5>
                    <Parameter label="Interpolation">
                        <ToggleSelect 
                            bind:value={values.orientationInterpolation}
                            options={[{label: "Follow", value: 1}, {label: "Slerp", value: 0}]}
                            on:change={() => {
                                if (values.orientationInterpolation === 0)
                                    $selectedCanvas.getOrientationSegment($time).setLinear();
                                if (values.orientationInterpolation === 1)
                                    $selectedCanvas.getOrientationSegment($time).setTracking();
                                animationController.updateCanvases();
                            }}
                        />
                    </Parameter>
                </div>
            </div>
            <div class="section">
                <div>
                    <Button on:click={exportKeyframes} disabled={!$selectedCanvas.trajectoryUpToDate}>
                        Export Keyframes
                    </Button>
                </div>
            </div>
        </div>

    {:else}
        Select a canvas to edit it.
    {/if}
</div>