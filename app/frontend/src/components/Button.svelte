<script>
	import { createEventDispatcher } from 'svelte';

	export let disabled = false;

	const dispatch = createEventDispatcher();

	function click() {
		dispatch('click');
	}
</script>

<style>

	button {
		color: inherit;
		background: transparent;
		font-size: inherit;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		border: solid 1px #DADADA;
		margin: 0;
	}

	button:hover {
		background: rgba(255, 255, 255, 0.1);
		transition: background-color 0.5s;
	}

	button:active {
		background: rgba(255, 255, 255, 0.2);
		transition: background-color 0.2s;
	}
	button:disabled {
		/* background-color: #cccccc; */
		cursor: wait;
		border-color: #666666;
		color: #666666;
	}

</style>

<button on:click={click} disabled={disabled}>
	<slot></slot>
</button>