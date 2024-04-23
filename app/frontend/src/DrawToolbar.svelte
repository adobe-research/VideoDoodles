<script>
    import Parameter from "./components/Parameter.svelte";
    import ToggleSelect from "./components/ToggleSelect.svelte";
    import ColorPicker from "./components/ColorPicker.svelte";
    import Slider from "./components/Slider.svelte";

    import { animationController } from './AnimationController.js';
    import { time } from './store.js';
    import Button from "./components/Button.svelte";

    let { selectedCanvas } = animationController;


    export let drawTools;

    function deleteStroke() {
        if (drawTools.mode === "edit") { 
            $selectedCanvas.deleteSelectedStrokes($time); 
            animationController.updateCanvases(); 
        } 
    }

</script>

<style>

    .container {
        background-color: rgb(37, 37, 37);
        /* flex: auto; */
        padding: 10px;
        display: flex;
        gap: 10px;
        flex-direction: row;
        align-items: center;
    }

</style>

<svelte:window 
    on:keydown={(e) => {if (e.code == "KeyX") { e.preventDefault(); deleteStroke(); } }}
/>

<div class='container'>
    <Parameter label="Tool">
        <ToggleSelect 
            bind:value={drawTools.mode} 
            options={[{value: "pencil", label: "Draw"}, {value: "edit", label: "Edit"}]} toggleKey="Shift"
            on:change={() => drawTools = drawTools}/>
    </Parameter>
    {#if drawTools.mode == "pencil"}
        <Parameter label="Color">
            <ColorPicker bind:value={drawTools.color} on:change={() => drawTools = drawTools}/>
        </Parameter>
        <Parameter label="Radius">
            <Slider bind:value={drawTools.width} min=1 max=60 on:change={() => drawTools = drawTools}/>
        </Parameter>
    {/if}
    {#if drawTools.mode == "edit"}
    <Parameter label="Stroke">
        <Button on:click={deleteStroke}>
            Delete
        </Button>
    </Parameter>
    {/if}
</div>