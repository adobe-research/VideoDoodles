<script>
    import {link, push} from 'svelte-spa-router';
    // import active from 'svelte-spa-router/active'

    import ToggleSelect from "./components/ToggleSelect.svelte";

    import { clipName, availableClips } from './store.js';
    import { send } from './websocket.js';

    import { saveToLoad } from './AnimationController';

    // Query the server for the list of videos available
    send({
        "action": "GET_VIDEO_LIST"
    });

    const BASE_URL = "data";

    // let saveFilePath = "";
    let saveFileInput;

    const fReader = new FileReader();

    // $: console.log(if (save) fReader.readAsDataURL(saveFilePath)), fetch(fReader.readAsDataURL(saveFilePath)).then((response) => console.log(response));


    function loadSaveFile() {
        fReader.readAsText(saveFileInput.files[0]);
        fReader.onload= (e) => {
            const fileData = JSON.parse(fReader.result);
            clipName.update(() => fileData.clip);
            saveToLoad.data = fileData;
            push(`/app/${fileData.clip}`)
            // animationController.loadExportedScene(fileData);
        };
    }

</script>

<style>
    .content {
        padding: 0 20px;
    }

    .desc {
        margin-bottom: 10px;
    }

    .video-gallery {
        display: flex;
        width: 100%;
        flex-direction: row;
        flex-wrap: wrap;
        gap: 10px;
        justify-content: center;
    }

    .vid-miniature {
        min-width: 200px;
        flex-basis: 20%;
    }

    video {
        width: 100%;
    }
</style>

<div class="content">
    <h1>Video doodles - Input gallery</h1>

    <div class="desc">
        Choose a video to add doodles to, or load a save file:
        <input type="file"
            id="save-file" name="save-file"
            accept=".json"
            bind:this={saveFileInput}
            on:change={loadSaveFile}
        />
    </div>

    <div class='video-gallery'>
        {#each $availableClips as video, vidIdx}
        <div class='vid-miniature'>
            <video id="stacked_vid" autoplay muted loop>
                <source src="{BASE_URL}/{video}/vid.mp4">
                <track kind="captions">
            </video>
            <a href="/#/app/{video}" target="_blank" rel="noreferrer noopener">
                {video}
            </a>
        </div>
        {/each}
    </div>
</div>