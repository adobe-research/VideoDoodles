<script>
    import {onMount, onDestroy, createEventDispatcher, afterUpdate, tick} from 'svelte';
    import * as THREE from 'three';
    import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
    import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";

    import vertexShader from './shaders/vertex.glsl';
    import fragmentShader from './shaders/sceneViewFromCanvasFragment.glsl';
    import ptsVertex from './shaders/ptsVertex.glsl';
    import ptsFragment from './shaders/ptsFragment.glsl';

    import { animationController } from './AnimationController.js';

    import { clipFrames, time } from './store.js';


    let { selectedCanvas } = animationController;


    export let viewportImage;
    export let width;
    export let height;
    export let style;

    export let triggerRender;

    export let skewness = 0;

    let threeDOMElement;

    let scene;
    let renderer;
    let composer;
    let camera;
    // let ptsCamera;
    // let composer;

    let viewPlaneMat;
    let viewPlaneGeom;

    // let pointCloudObject;
    // let ptsMaterial;

    let viewSlice = 0;

    // $: $selectedCanvas, $time, setTexture();

    $: width, height, resizeCanvasToDisplaySize();

    // $: $time, setPointCloud();


    function setTexture() {

        if (viewPlaneMat && $selectedCanvas) {
            // console.log("set texture");
            // if (viewPlaneMat.uniforms["viewportImage"].value) {
            //     viewPlaneMat.uniforms["viewportImage"].value.needsUpdate = true;
            // }
            // else {
                // console.log("creating canvas texture")

            if (viewPlaneMat.uniforms.viewportImage.value)
                viewPlaneMat.uniforms.viewportImage.value.dispose();

            viewPlaneMat.uniforms["viewportImage"].value = new THREE.CanvasTexture(viewportImage);
            // }

            viewPlaneMat.needsUpdate = true;
                
            // console.log("setting viewportImage");
            // console.log(viewportImage);
            // console.log(new THREE.Vector2(viewportImage.width, viewportImage.height));

            viewPlaneMat.uniforms["viewportResolution"].value = new THREE.Vector2(viewportImage.width, viewportImage.height);

            viewPlaneMat.uniforms["rot"].value = $selectedCanvas.getRotation($time);
            viewPlaneMat.uniforms["pos"].value = $selectedCanvas.getPosition($time);
            viewPlaneMat.uniforms["scale"].value = $selectedCanvas.canvas.scale;
            viewPlaneMat.uniforms["VP"].value = $clipFrames[$time].getVP();

            // // Align ptsCamera to plane
            // const canvasPos = $selectedCanvas.getPosition($time);
            // ptsCamera.position.set(canvasPos.x, canvasPos.y, canvasPos.z);
            // const canvasRot = new THREE.Quaternion();
            // canvasRot.setFromRotationMatrix($selectedCanvas.getRotation($time));
            // const inverseRot = new THREE.Quaternion();
            // inverseRot.setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI);
            // ptsCamera.quaternion.set(canvasRot.x, canvasRot.y, canvasRot.z, canvasRot.w);

            // ptsCamera.zoom = 1 / $selectedCanvas.canvas.scale;

            // ptsCamera.updateMatrix();
            // ptsCamera.updateProjectionMatrix();

            skewness = $selectedCanvas.getProjectedSkewness($time, viewportImage.width, viewportImage.height);

            // console.log(skewness);

            render();
        }
    }

    // function setPointCloud() {
    //     console.log("set point cloud");

    //     // Delete previous point cloud
    //     if (pointCloudObject && pointCloudObject.isObject3D) {
    //         scene.remove(pointCloudObject);
    //         pointCloudObject.geometry.dispose();
    //     }

    //     // Add point cloud view
    //     const frame = $clipFrames[$time];

    //     frame.loadDebugPoints().then(
    //         (bufferGeometry) => {

    //             pointCloudObject = new THREE.Points( bufferGeometry, ptsMaterial );
    //             scene.add( pointCloudObject );
    //             pointCloudObject.layers.set(1);

    //             render();

    //         }
    //     );

    // }


    onMount(() => {
        console.log("mount")

        triggerRender = () => { setTexture(); }

        renderer = new THREE.WebGLRenderer({ canvas: threeDOMElement });
        renderer.setSize( window.innerWidth, window.innerHeight );

        // composer = new EffectComposer( renderer );

        // Define scene and base elements
        scene = new THREE.Scene();
        scene.background = new THREE.Color(1, 1, 1);

        // Set up camera
        camera = new THREE.OrthographicCamera( - 1, 1, 1, - 1, 0, 1 );

        // const renderPass = new RenderPass( scene, camera );
        // composer.addPass( renderPass );

        // ptsCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, viewSlice - 0.1, viewSlice + 0.1);
        // ptsCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -1, 1);
        // ptsCamera.layers.enable(1);

        // const renderPtsPass = new RenderPass( scene, ptsCamera );
        // composer.addPass( renderPtsPass );


        // View aligned plane (for the frames and depth maps)
        viewPlaneGeom = new THREE.BufferGeometry();
        let z = 0.0;
        viewPlaneGeom.setAttribute( 'position', new THREE.BufferAttribute( new Float32Array([   -1,-1,z, 1,-1,z, 1,1,z, -1, -1, z, 1, 1, z, -1, 1, z]), 3 ) );

        // console.log(viewportImage);

        viewPlaneMat = new THREE.ShaderMaterial({
            uniforms :{
                resolution: { value: new THREE.Vector2( threeDOMElement.width, threeDOMElement.height ) },
                viewportImage: { value: undefined },
                viewportResolution: { value: viewportImage ? new THREE.Vector2(viewportImage.width, viewportImage.height) : new THREE.Vector2(1, 1) },
                VP: { value: new THREE.Matrix4() },
                rot: { value: new THREE.Matrix4() },
                pos: { value: new THREE.Vector3() },
                scale: { value: 1.0 },
            },
            vertexShader : vertexShader,
            fragmentShader : fragmentShader,
            transparent: true,
            depthWrite: false,
            // side: THREE.DoubleSide
        });


        const viewPlane = new THREE.Mesh( viewPlaneGeom, viewPlaneMat );

        viewPlane.renderOrder = 0;

        // This is essential, otherwise the plane will sometimes get culled!
        viewPlane.frustumCulled = false;

        scene.add( viewPlane );

        // ptsMaterial = new THREE.ShaderMaterial( {
        //     uniforms: {
        //         size: { value: 10 }
        //     },
        //         vertexShader: ptsVertex,
        //         fragmentShader: ptsFragment,
        //         transparent: false,
        //     } );

        setTexture();

    });

    onDestroy(() => {
        if (viewPlaneMat.uniforms.viewportImage.value)
            viewPlaneMat.uniforms.viewportImage.value.dispose();
        viewPlaneMat.dispose();
        viewPlaneGeom.dispose();
    })


    function resizeCanvasToDisplaySize() {
        // console.log(width);
        if (!renderer)
            return;

        renderer.setSize(width, height, true);
        viewPlaneMat.uniforms.resolution.value = new THREE.Vector2(width, height);

    }

    function render() {
        // requestAnimationFrame( render );

        if (!renderer)
            return;

        console.log("rendering from canvas");
        renderer.render(scene, camera);

    }

    // function updateViewSlice() {
    //     console.log(viewSlice);
    //     ptsCamera.near = viewSlice - 0.1;
    //     ptsCamera.far = viewSlice + 0.1;

    //     ptsCamera.updateProjectionMatrix();

    //     render();
    // }


    afterUpdate(() => {
        resizeCanvasToDisplaySize();
    })


</script>

<style>
    #three-scene-in-canvas {
        position: absolute;
        top: 0;
        left: 0;
    }
</style>

<canvas id="three-scene-in-canvas" bind:this={threeDOMElement} style={style}></canvas>