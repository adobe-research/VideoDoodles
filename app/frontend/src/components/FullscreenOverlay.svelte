<script>
    export let opacity = 0.5;
    export let priority = 0;
</script>


<style>
    .overlay {
        position: fixed; /* Sit on top of the page content */
        width: 100%; /* Full width (cover the whole page) */
        height: 100%; /* Full height (cover the whole page) */
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0,0,0,var(--overlay-opacity)); /* Black background with opacity */
        z-index: 1000;
        color: white;
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 2em;
        text-align: center;
        flex-direction: column;
        gap: 10px;
    }
</style>


<div class="overlay" style="--overlay-opacity: {opacity}; z-index: {1000 + priority}">
    <slot></slot>
</div>