<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	function change() {
		value = selectElement.value;
		console.log(selectElement);
		dispatch('change');
	}

	function getValue(option) {
		return option.value === undefined ? option : option.value;
	}

	function getLabel(option) {
		return option.label === undefined ? option : option.label;
	}

	export let options;
	export let value;
	// export let toggleKey;

	// let selectedIdx = 0;
	// $: setValue(value);
	// $: options, setValue(value);

	let togglingDirection = 1;

	let selectElement;

	function setValue(newValue) {
		console.log("changed value to " + newValue);
		// selectedIdx = options.findIndex((el) => {return getValue(el) == newValue});
		// console.log(options);
		// console.log(selectedIdx);
	}


</script>

<style>
	.container {
		font-size: 0.8em;
		cursor: pointer;
		user-select: none;
		border-radius: 2px;
		border: solid 1px #DADADA;
		display: flex;
		margin: 0 0 0.5em 0;
		background-color: inherit;
    	color: inherit;
	}

	.option {
		flex: 1;
		text-align: center;
        padding: 7px;
		font-weight: 400;
	}

	.option:not(:last-child) {
		border-right: solid 1px #DADADA;
	}

	.option:hover {
		background: rgba(255, 255, 255, 0.1);
        transition: background-color 0.5s;
	}

	.option:active {
		background: rgba(255, 255, 255, 0.2);
		transition: background-color 0.2s;
	}

</style>


<!-- <svelte:window 
	on:keydown={
		(e) => {
			if (toggleKey && e.key == toggleKey) { e.preventDefault(); change((selectedIdx + togglingDirection + options.length) % options.length) } 
			if (toggleKey && e.key == "Shift") { togglingDirection = -1; }
		}} 
	on:keyup={
		(e) => {
			if (e.key == "Shift") { togglingDirection = 1;  } 
		}}
/> -->
<!-- <svelte:window on:keyup={(e) => {if (toggleKey ) console.log(e.code, toggleKey);}} /> -->

<select class="container" on:change={change} bind:this={selectElement}>
<!-- <div class="container"> -->
	{#each options as option, idx}
		<option class="option" value={getValue(option)} selected={getValue(option) === value}>
			{getLabel(option)}
		</option>
	{/each}
<!-- </div> -->
</select>