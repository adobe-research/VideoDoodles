<script>

    import Slider from "./components/Slider.svelte";
    import IconButton from "./components/IconButton.svelte";

    import { clipFrames, time } from './store.js';

    import { sessionLog, LogActionType } from "./SessionLog";


    // export let allFrames = [];
    // export let currentFrameId = 0;

    let play = false;
    const FPS = 30;

    
    animate();


    function animate() {

        if ($time >= $clipFrames.length - 1) {
            play = false;
        }

        if (play) {
            time.update(t => t+1);
        }

        // setTimeout(animate, 1000 / FPS)

        setTimeout(() => {
            requestAnimationFrame(animate);
        }, 1000 / FPS);
    }
            


</script>

<style>

    .container {
        background-color: rgb(37, 37, 37);
        /* flex: auto; */
        padding: 5px;
    }

    .centered-row {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }

</style>



<div class='container'>
    <div class="centered-row">
        <IconButton disabled={$time == 0} on:click={() => time.update(t => 0)}>
            <i class="material-icons">first_page</i>
        </IconButton>
        <IconButton disabled={$time == 0} on:click={() => time.update(t => t-1)}>
            <i class="material-icons">skip_previous</i>
        </IconButton>
        <IconButton on:click={() => { play = !play; sessionLog.log(LogActionType.NavigateTime, {time: $time, type: play? "play" : "pause"});}}>
            {#if !play}
                <i class="material-icons">play_arrow</i>
            {:else}
                <i class="material-icons">pause</i>
            {/if}
        </IconButton>
        <IconButton disabled={$time >= $clipFrames.length - 1} on:click={() => time.update(t => t+1)}>
            <i class="material-icons">skip_next</i>
        </IconButton>
        <IconButton disabled={$time >= $clipFrames.length - 1} on:click={() => time.update(t => $clipFrames.length - 1)}>
            <i class="material-icons">last_page</i>
        </IconButton>
        <div>
            Frame&nbsp;{$time + 1}/{$clipFrames.length}
        </div>
    </div>
    <!-- <div class="centered-row">
        <div>
            Frame&nbsp;1
        </div>
        <Slider min={0} max={allFrames.length - 1} step={1} bind:value={currentFrameId}/>
        <div>
            Frame&nbsp;{currentFrameId + 1}/{allFrames.length}
        </div>
    </div> -->
</div>