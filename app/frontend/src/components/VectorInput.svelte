<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	function change() {
		dispatch('change', {
			value: values
		});
	}

	export let values = {};
    export let labels = [];
	export let min = -100;
	export let max = 100;
	export let step = 0.1;

    export let disabled = false;

</script>

<style>
    .container {
        display: flex;
        gap: 5px;
    }

    .dim {
        display: flex;
        flex-direction: column;
        font-size: 0.8em;
    }

    label {
        margin-bottom: 0.2em;
    }

    input {
        background-color: inherit;
        color: inherit;
        padding: 0.1em;
    }

</style>

<div class="container">
    {#each labels as label, i}
        <div class="dim">
            <label for="vector-{i}">{labels[i]}</label>
            <input 
                class:loading={disabled}
                disabled={disabled}
                on:change={change}
                bind:value={values[label]}
                type="number" 
                {min} {max} {step}
                id="vector-{i}"
            >
        </div>
    {/each}
</div>