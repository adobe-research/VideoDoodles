<script>
    import { createEventDispatcher } from 'svelte';

    import DropdownSelect from "./components/DropdownSelect.svelte";
    import Parameter from "./components/Parameter.svelte";
    import Slider from "./components/Slider.svelte";
    import ToggleSelect from "./components/ToggleSelect.svelte";
    import Button from "./components/Button.svelte";

    export let parameters;
    export let actions

    // $: console.log(parameters);

	const dispatch = createEventDispatcher();

	function click(e) {
		dispatch(e);
	}

</script>

<style>

    .container {
        background-color: rgb(37, 37, 37);
        /* flex: auto; */
        padding: 10px;
    }

</style>

<div class='container'>
    {#each Object.entries(parameters) as [key, parameter]}
        {#if parameter.exposed}
        <Parameter label={parameter.label}>
            {#if parameter.type == "slider"}
                <Slider bind:value={parameter.value} {...parameter.options} on:change={() => parameters = parameters}/>
            {:else if parameter.type == "toggle"}
                <ToggleSelect bind:value={parameter.value} {...parameter.options} on:change={() => parameters = parameters}/>
            {:else if parameter.type == "dropdown"}
                <DropdownSelect bind:value={parameter.value} {...parameter.options} on:change={() => parameters = parameters}/>
            {/if}
        </Parameter>
        {/if}
    {/each}
    <div style="margin-top: 10px">
    {#each Object.entries(actions) as [key, action]}
        {#if action.exposed}
            <Button on:click={() => dispatch(action.event)}>
                {action.label}
            </Button>
        {/if}
    {/each}
    </div>
</div>