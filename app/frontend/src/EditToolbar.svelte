<script>
    // import DropdownSelect from "./components/DropdownSelect.svelte";
    import Parameter from "./components/Parameter.svelte";
    // import Slider from "./components/Slider.svelte";
    import ToggleSelect from "./components/ToggleSelect.svelte";

    import { animationController } from "./AnimationController.js";


    export let editTool = "move";

</script>

<style>

    .container {
        background-color: rgb(37, 37, 37);
        /* flex: auto; */
        padding: 10px;
    }

</style>

<svelte:window 
    on:keydown={(e) => {if (e.code == "KeyA") { e.preventDefault();  animationController.addCanvas(); editTool = "move"; } }}
    on:keydown={(e) => {if (e.code == "KeyX") { e.preventDefault(); animationController.deleteSelectedCanvas(); } }}

    on:keydown={(e) => {if (e.code == "KeyT") { e.preventDefault(); editTool = "move" } }}
    on:keydown={(e) => {if (e.code == "KeyR") { e.preventDefault(); editTool = "rotate" } }}
/>

<div class='container'>
    <Parameter label="Tool">
        <ToggleSelect bind:value={editTool} options={["move", "rotate"]}/>
    </Parameter>
</div>