<script>
	export let label = '';
	export let hint;
	export let hintLeftSide = false;
	export let row = false;
	export let centered = false;

	let showHint = false;
	let hintPosTop = "20px";
	let hintPosLeft = "100px";

	function handleMouseMove(e) {
		hintPosTop = (e.clientY + 5) + "px";
		if (!hintLeftSide) {
			hintPosLeft = (e.clientX + 5) + "px";
		}
		else {
			hintPosLeft = Math.max(e.clientX + 5 - 300, 0) + "px";
		}
	}
</script>

<style>
	.parameter {
		/* padding: 5px; */
		-webkit-user-select: none; /* Safari */        
		-moz-user-select: none; /* Firefox */
		-ms-user-select: none; /* IE10+/Edge */
		user-select: none; /* Standard */
	}

	.row .label {
		margin-right: 5px;
	}

	.label{
		padding-bottom: 5px;
		font-size: 0.8em;
		/* font-weight: 600; */
		display: flex;
        align-items: center;
	}

	.label.centered {
		justify-content: center;
	}

	/* .label .material-icons {
		font-size: 1.1em;
		padding: 0 10px;
		cursor: help;
	} */

	.hint {
		position: fixed;
		z-index: 10;
		top: var(--pos-top);
		left: var(--pos-left);
        background: rgb(227, 227, 227);
        padding: 5px;
        border-radius: 6px;
		width: 300px;
		font-size: 0.9em;
	}

</style>

<svelte:window on:mousemove={handleMouseMove}/>

<div class="parameter" class:row={row}>
	<div class="label" class:centered={centered}
		on:mouseleave={() => {showHint = false;} }>
		{label}
		{#if hint}
			<!-- <i class="material-icons"  on:mouseover={() => {showHint = true;}} >
				help
			</i> -->
		{/if}
	</div>
	<slot></slot>
</div>

{#if hint && showHint}
	<div class="hint" style="--pos-left: {hintPosLeft}; --pos-top: {hintPosTop};">
		{@html hint}
	</div>
{/if}