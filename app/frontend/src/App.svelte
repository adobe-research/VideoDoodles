<script>
    import Viewport from "./Viewport.svelte";
    import Timeline from "./Timeline.svelte";
    import DrawingCanvas from "./DrawingCanvas.svelte";
    import KeyframeTimeline from "./KeyframeTimeline.svelte";
    import Parameters from "./Parameters.svelte";
    import Message from "./Message.svelte";
    import CanvasProperties from "./CanvasProperties.svelte";
    import EditToolbar from "./EditToolbar.svelte";
    import FullscreenOverlay from "./components/FullscreenOverlay.svelte";
    import Button from "./components/Button.svelte";


    import { animationController } from "./AnimationController.js";

    import { clipFrames, clipName, time, criticalErrorMessage, dialogProps } from './store.js';
    // import { send } from './websocket.js';
    import DrawToolbar from "./DrawToolbar.svelte";

    import { sessionLog } from "./SessionLog.js";
    import PopupDialog from "./components/PopupDialog.svelte";
    import { mode } from "d3";

    // Query the server for the list of videos available
    // send({
    //     "action": "GET_VIDEO_LIST"
    // });

    export let params;

    $: {
        if (params && params.videoName) {
            changeFootage(params.videoName);
        }
    }


    const canvasDim = 400;


    let loadingFrames = false;
    let loadingPercent = 0;


    let parameters = {
        // videoClip: { value: "train", label: "Clip", type: "dropdown", options: {options: []}, exposed: true},
        show3DView: { value: false, label: "3D View", type: "toggle", options: {options: [{value: false, label: "Hide"}, {value: true, label: "Show"}]}},
        mode: { value: "edit", label: "Mode", type: "toggle", options: {options: [{value: "view", label: "View"}, {value: "edit", label: "Edit"}, {value: "draw", label: "Draw"}], toggleKey: "Tab"}, exposed: true},
        // showCanvasDebug: { value: true, label: "Canvas Debug View", type: "toggle", options: {options: [{value: false, label: "Hide"}, {value: true, label: "Show"}]}, exposed: true},
        // frameOpacity: { value: 1.0, label: "Frame Opacity", type: "slider", options: {min: 0, max: 1, step: 0.1}, exposed: true},
    }

    let actions = {
        export: {label: "Export", event: "exportAction", exposed: false}
    }

    $ : {
        if (parameters.mode.value === "view")
            actions.export.exposed = true;
        else
            actions.export.exposed = false;
    }

    let editTool;

    let drawTools = {
        "mode": "pencil",
        "color": "white",
        "width": 10
    }


    // $ : parameters.videoClip.options.options = $availableClips;
    // clipName.update(() => $availableClips[0]);

    // $ : changeFootage(parameters.videoClip.value);

    // $ : placeCanvas($canvasTransformData);

    // $ : animationController.setTime(currentFrameId);
    $ : $time, animationController.update();

    let triggerRender;
    let triggerExport;

    function changeFootage(videoClip) {
        // if (videoClip != currentVideoClip) {
        //     currentVideoClip = videoClip;

            animationController.reset(); // this is done in Viewport onMount, otherwise loading save file does not work.
            clipName.update(() => videoClip);
            time.update(() => 0);
            parameters.mode.value = "edit";
            sessionLog.startSession();
        // }
        
    }

    function handleViewportRender() {
        if (parameters.mode.value === "draw" && triggerRender) {
            triggerRender();
        }
    }

    function handleExportClick() {
        dialogProps.set(
            {
                active: true,
                title: "Export",
                message: "Export current results? This will take some time to render all frames.",
                onCancel: () => {},
                onOkay: () => { triggerExport(); }
            }
        )
    }


    let viewportImage;

    function beforeUnload(event) {
        // Cancel the event as stated by the standard.
        event.preventDefault();
        // Chrome requires returnValue to be set.
        event.returnValue = '';
        console.log("unload?")
        // more compatibility
        return '...';
    }



</script>

<style>
    .app {
        background-color: rgb(17, 17, 17);
        height: 100%;
        display: flex;
        flex-direction: column;
        gap: 5px;
        color: white;
    }

    .row {
        display: flex;
        gap: 5px;
    }

    .main {
        flex-grow: 1;
        max-height: 80%;
    }

    .stacked-sidebar {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

</style>

<svelte:window on:beforeunload={beforeUnload} on:hashchange={beforeUnload}/>

{#if $criticalErrorMessage.length > 0}
<FullscreenOverlay opacity={1} priority={10}>
    <div>
        Critical error occured: 
        <br/>
        {$criticalErrorMessage}
    </div>
    <Button on:click={() => triggerExport()}>
        Export result?
    </Button>
</FullscreenOverlay>
{/if}

{#if $dialogProps.hasOwnProperty("active") && $dialogProps.active}
    <PopupDialog active={$dialogProps.active}/>
{/if}

<div class="app">
    <div class="row main">
        
        <Parameters bind:parameters actions={actions} on:exportAction={handleExportClick}/>

        <Viewport 
            bind:triggerExport={triggerExport}
            bind:threeDOMElement={viewportImage}
            parameters={parameters} 
            editTool={editTool}
            on:rendered={handleViewportRender}
            />
        {#if parameters.mode.value === "draw"}
        <div class="stacked-sidebar" style="width: 25%;">
            <DrawToolbar bind:drawTools={drawTools}/>
            <DrawingCanvas 
                drawTools={drawTools}
                bind:triggerRender={triggerRender} 
                viewportImage={viewportImage} 
                canvasDim={canvasDim}/>
        </div>
        {/if}
        {#if parameters.mode.value === "edit"}
        <div class="stacked-sidebar">
            <EditToolbar bind:editTool={editTool}/>
            <CanvasProperties/>
        </div>
        {/if}

    </div>

    <Timeline/>

    <KeyframeTimeline uneditable={parameters.mode.value !== "edit"} drawMode={parameters.mode.value === "draw"} viewportImage={viewportImage}/>

    <Message />
</div>
