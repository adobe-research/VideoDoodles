

<script>
    import {onMount, afterUpdate} from 'svelte';

    import { Vector2 } from 'three';


    export let frameWidth = 0;
    export let frameHeight = 0;

    export let drawingCanvas;

    let drawingContext;

    let tool = "pencil";

    let painting = false;
    const drawStartPos = new Vector2();


    onMount(() => {
        drawingContext = drawingCanvas.getContext( '2d' );
    });

    function start(e) {
        painting = true;
        drawStartPos.set( e.offsetX, e.offsetY );
        // console.log({x: e.offsetX, y: e.offsetY})
    }

    function draw(e) {
        if ( painting && drawingContext ) {
            let x = e.offsetX;
            let y = e.offsetY;

            drawingContext.beginPath();

            if(tool=='pencil') {
                drawingContext.globalCompositeOperation = 'source-over';
                drawingContext.lineWidth = 5;
            }
            else {
                drawingContext.globalCompositeOperation = 'destination-out';
                drawingContext.lineWidth = 15;
            }

            drawingContext.moveTo( drawStartPos.x, drawStartPos.y );
            drawingContext.strokeStyle = 'black';
            drawingContext.lineCap = 'round';
            drawingContext.lineTo( x, y );
            drawingContext.stroke();

            // reset drawing start position to current position.
            drawStartPos.set( x, y );
        }
    }

    function stop(e) {
        painting = false;
    }

    export const initImage = (image, x, y, w, h) => {
        if (drawingContext) {
            x = Math.round(x * drawingCanvas.width);
            w = Math.round(w * drawingCanvas.width);
            y = Math.round(y * drawingCanvas.height);
            h = Math.round(h * drawingCanvas.height);
            console.log("drawing image at " + x + " " + y + " " + w + " " + h);
            let texImage = new ImageData(image.data, image.width, image.height);
            createImageBitmap(texImage).then((im) => {
                drawingContext.drawImage(im, 0, 0, image.width, image.height, x, y, w, h);
            })
        }
    }


</script>

<svelte:window 
    on:keydown={(e) => {if (e.key == "Shift") { e.preventDefault(); console.log("erase"); tool = "eraser"  } }}
    on:keyup={(e) => {if (e.key == "Shift") { e.preventDefault(); tool = "pencil"  } }}
/>

<canvas 
    width={frameWidth} 
    height={frameHeight}
    bind:this={drawingCanvas}
    on:pointerdown={start}
    on:pointermove={draw}
    on:pointerleave={stop}
    on:pointerup={stop}
    >
</canvas>