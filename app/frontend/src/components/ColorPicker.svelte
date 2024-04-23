<script>
	// v1.2 - added keyboard nav for colors
	// @todo still a bug when the dropdown opens, we should focus on the already selected color, this only works when you click it open, close it and open again

	// import { v4 as uuid } from '@lukeed/uuid';
	import { clickOutside } from './clickOutside.js';
	import { tick, onMount, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	
	// Initial value
	export let id = 0;
	export let value = '#5E7ABC';

	// Our color set
	let values = [
		['#ffffff', '#DAAFE9', '#C7DBF5', '#AAD5FB', '#ADE5DA', '#B0EDC3', '#FDF0A4', '#F8D6A2', '#EF9A9A'],
		['#999999', '#C47ADA', '#90BAEE', '#75BAFA', '#72D5BF', '#73DE8C', '#FBE66E', '#F5B969', '#EF5350'],
		['#333333', '#AE44B7', '#5E7ABC', '#5E7ABC', '#4DACA9', '#63B75A', '#EDBD4A', '#EC9740', '#E53935'],
		['#000000', '#501B87', '#021B6B', '#0C2794', '#337277', '#2F6A52', '#AE802F', '#AD6127', '#B71C1C']
  ]

	 // Keyboard shortcut
  let trigger = 'Escape';
  function handleKeydown(e) {
    if (e.key == trigger) {
      ddActive = false;
    }
  }

	let windowHeight;
	let top;

	let ddActive = false;
	
	let ddHeight = 158;
	// ddHeight is initially undefined so we can't get the correct values from binding; that's why we have a default
	// todo render offscreen for .1sec to get the height automatically?
	
	let inputHeight;

	async function toggleDropdown(e) {
		if (
			(e.clientY + inputHeight) < ddHeight
			||
			(windowHeight - ddHeight - inputHeight - e.clientY) > 0
		) {
			top = false;
		} else {
			top = true;
		}
		
		ddActive = !ddActive

		await tick();
		if (ddActive) {
			//document.querySelector('.color-block.active').focus();
		}
	}
	

	function clickOutsideDropdown() {
		ddActive = false;
	}

	function changeValue(innerValue) {
		value = innerValue;
		ddActive = false;
		dispatch('change');
	}
	
	function keyboardGridNav(e, index) {
	
	 
	 const focussedElement = document.activeElement.id;
	 
	 let myRow = parseInt(focussedElement.charAt(focussedElement.length-3));
	 let myIndex = parseInt(focussedElement.charAt(focussedElement.length-1));
	 let nextRow;
	 let prevRow;
	 let nextIndex;
	 let prevIndex;

	 switch(e.keyCode) {
		// left arrow
		case 37: 
				prevIndex = myIndex-1;
			 if (prevIndex > -1) {
					document.getElementById(id+'-'+myRow+'-'+prevIndex).focus();
				}
				break;
		// top arrow
		case 38: 
				prevRow = myRow-1;
				if (prevRow > -1) {
					document.getElementById(id+'-'+prevRow+'-'+myIndex).focus();
				}
				break;
		// right arrow
		case 39: 
				nextIndex = myIndex+1;
				  if ( nextIndex < values[0].length) {
						document.getElementById(id+'-'+myRow+'-'+nextIndex).focus();
					}
					break;
				 // down arrow
			case 40: 
				 	nextRow = myRow+1;
				  if (nextRow < values.length) {
						document.getElementById(id+'-'+nextRow+'-'+myIndex).focus();
					}
					break;          
				}

	}

</script>

<svelte:window bind:innerHeight={windowHeight} on:keydown={handleKeydown} />

<div class="color-picker-holder">
<div class="color-picker-inner"  >
	<button bind:clientHeight={inputHeight} class="select-color" on:click={(e) => toggleDropdown(e)} class:fake-focus={ddActive}>
		<div style="display: flex;">
			<div style="background: {value};" class="color-block"></div>
			<div class="caret" class:top={top} style="margin-right: .2rem;"></div>
		</div>
	</button>
	<!-- <input type="text" bind:value> -->
	
</div>

{#if ddActive}
<div class:top={top} bind:clientHeight={ddHeight} class="values-dropdown" use:clickOutside on:click_outside={clickOutsideDropdown}>
	<div class="values-dropdown-grid">
	{#each values as val, index}
		{#each val as innerValue, innerIndex}
			<button
					id="{id}-{index}-{innerIndex}"
					class:active={innerValue == value}
					on:keydown={(e) => keyboardGridNav(e,  innerIndex)}
					style="background: {innerValue};"
					on:click={() => { changeValue(innerValue) }}
					class="color-block">
				</button>
		{/each}
	{/each}
			</div>
	</div>
	{/if}
</div>


<style>
	
	.color-picker-holder {
		position: relative;
	}
	
	.color-picker-inner {
		display: flex;
		height: 35px;
	}
	
	.select-color {
		border: 1px solid #CCC;
		padding: 3px;
		border-radius: .2rem;
		margin-right: .4rem;
		background: #FFF;
		height: 35px;
	}
	
	.caret {
	  width: 0; 
	  height: 0; 
	  border-left: 4px solid transparent;
	  border-right: 4px solid transparent;
	  border-top: 4px solid #555;
		position: relative;
		top: 10px;
		margin-left: 4px;
	}	

	.caret.top {
	  border-left: 4px solid transparent;
	  border-right: 4px solid transparent;
	  border-bottom: 4px solid #555;
		border-top: none;
	}
	
	.active {
		box-shadow: inset 0 0 0 1px #FFF, 0 0 3px 1px rgba(0,0,0,0.25);
	}
	
	.fake-focus, button:focus  {
		outline: 0;
		box-shadow: 0 0 0 2px #18A0FB;
		border-color: #18A0FB;
	}
	
	/* input {
		border: 1px solid #CCC;
		height: 35px;
		border-radius: .2rem;
	} */
	
	.color-block {
		border-radius: .2rem; width: 18px; height: 18px; line-height: 0; font-size: 0;
		border: 1px #666666 solid;
	}
	
	.values-dropdown {
		padding: 1rem;
		position: absolute;
		z-index: 20;
		top: 40px;
		background: white;
		border: 1px solid #CCC;
		border-radius: .3rem;
	}
	
	.values-dropdown-grid {
		grid-template-columns: repeat(9, 18px);
		grid-template-rows: 18px 18px;
		grid-gap: 5px;
		display: grid;
	}
	
	.values-dropdown.top {
		top: auto;
		bottom: 40px;
	}
	
	
</style>

