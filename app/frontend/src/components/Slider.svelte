<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	function change() {
		dispatch('change', {
			value: value
		});
	}

	export let value;
	export let min;
	export let max;
	export let step;
</script>

<style>
	.slider {
		-webkit-appearance: none;
		width: 100%;
		height: 8px;
		padding: 0;
		margin: 0;
		border-radius: 4px;   
		background: #d3d3d3;
		outline: none;
		opacity: 0.7;
		-webkit-transition: .2s;
		transition: opacity .2s;
	}

	.slider:hover {
		opacity: 1; /* Fully shown on mouse-over */
	}

	.slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 18px;
		height: 18px;
		border-radius: 50%; 
		background: #4EB2DD;
		cursor: pointer;
	}

	.slider::-moz-range-thumb {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: #4EB2DD;
		cursor: pointer;
	}
</style>

<input type='range'
	class="slider"
	bind:value={value}
	{min} {max} {step}
	on:input={change}
/>