<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	function click() {
        if (!disabled)
    		dispatch('click');
	}

	export let disabled = false;

</script>

<style>

	button {
		color: inherit;
		background: transparent;
		font-weight: inherit;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		border: none;
		padding: 5px;
		margin: 0;
        border-radius: 100%;
	}

	button:not(.disabled):hover {
		background: rgba(255, 255, 255, 0.1);
		transition: background-color 0.5s;
	}

	button:not(.disabled):active {
		background: rgba(255, 255, 255, 0.2);
		transition: background-color 0.2s;
	}

	.disabled {
		cursor: default;
		opacity: 0.3;
	}

</style>

<button class:disabled on:click={click}>
	<slot></slot>
</button>