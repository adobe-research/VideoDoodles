<script>
    import FullscreenOverlay from "./FullscreenOverlay.svelte";
    import Button from "./Button.svelte";

    import { dialogProps } from "../store";
      
    function _onCancel() {
        $dialogProps.onCancel();
        dialogProps.set({});
    }
    
    function _onOkay() {
        $dialogProps.onOkay();
        dialogProps.set({});
    }
      
</script>

<style>
    .container {
        display: block;
        background: white;
        color: black;
        padding: 20px;
        border-radius: 10px;
        max-width: 80%;
    }

    h2 {
        font-size: 2rem;
        text-align: center;
    }

    .message {
        font-size: 0.8em;
    }
    
    .buttons {
        display: flex;
        justify-content: space-between;
        font-size: 0.8em;
        margin-top: 10px;
    }
    
</style>
  
<FullscreenOverlay>
    <div class="container">
        <h2>{$dialogProps.title}</h2>

        <div class="message">
            {$dialogProps.message}
        </div>
    
        <div class="buttons">
            <Button on:click={_onCancel}>
                Cancel
            </Button>
            <Button on:click={_onOkay}>
                Okay
            </Button>
        </div>
    </div>
</FullscreenOverlay>