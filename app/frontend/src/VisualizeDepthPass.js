
import * as THREE from "three";
import { Color } from "three";
import { Pass } from "three/examples/jsm/postprocessing/Pass.js";
import { FullScreenQuad } from "three/examples/jsm/postprocessing/Pass.js";
import { CopyShader } from 'three/examples/jsm/shaders/CopyShader.js';

import fragmentShader from "./shaders/depthVisFragment.glsl";


class VisualizeDepthPass extends Pass {
	constructor(resolution, scene, camera) {
		super();

		this.renderScene = scene;
		this.camera = camera;
		this.resolution = new THREE.Vector2(resolution.x, resolution.y);

		this.fsQuad = new FullScreenQuad(null);
		this.fsQuad.material = this.createMaterial();


        const target = new THREE.WebGLRenderTarget( resolution.x, resolution.y );
        target.texture.minFilter = THREE.NearestFilter;
        target.texture.magFilter = THREE.NearestFilter;
        target.stencilBuffer = false;
        target.depthTexture = new THREE.DepthTexture();
        // target.depthTexture.format = format;
        // target.depthTexture.type = type;

        this.target = target;

        // Create a temporary buffer to render the canvases onto
        // const canvasTarget = new THREE.WebGLRenderTarget(
        //     100, 100
        // );

        // canvasTarget.texture.generateMipmaps = false;

        // this.canvasTarget = canvasTarget;

        console.log("init pass")

		// Create a buffer to store the normals of the scene onto
		// const normalTarget = new THREE.WebGLRenderTarget(
		// 	this.resolution.x,
		// 	this.resolution.y
		// );
		// normalTarget.texture.format = THREE.RGBFormat;
		// normalTarget.texture.minFilter = THREE.NearestFilter;
		// normalTarget.texture.magFilter = THREE.NearestFilter;
		// normalTarget.texture.generateMipmaps = false;
		// normalTarget.stencilBuffer = false;
		// this.normalTarget = normalTarget;

		// this.normalOverrideMaterial = new THREE.MeshNormalMaterial();
	}

	dispose() {
		// this.canvasTarget.dispose();
		this.fsQuad.dispose();
	}

	setSize(width, height) {
		// this.canvasTarget.setSize(width, height);
		this.resolution.set(width, height);
        this.target.setSize(width, height);

        // this.fsQuad.material.uniforms.pixelSize.value = new THREE.Vector2(1 / this.resolution.x, 1 / this.resolution.y);
	}

	render(renderer, writeBuffer, readBuffer) {

		// 1. Re-render the scene to get only the semi transparent canvases
		// renderer.setRenderTarget(this.canvasTarget);
        // renderer.setClearColor( new Color(1, 1, 1), 0 );
        // renderer.clear();

        // // Render only things on layer 1
        // this.camera.layers.set(1);
        // const currentBackground = this.renderScene.background;
        // this.renderScene.background = null;
		// renderer.render(this.renderScene, this.camera);

        // this.renderScene.background = currentBackground;

		// this.fsQuad.material.uniforms["strokesBuffer"].value = this.canvasTarget.texture;
		// this.fsQuad.material.uniforms["sceneColorBuffer"].value = readBuffer.texture;

        // // Reset camera layers
        // this.camera.layers.set(0);



        renderer.setRenderTarget( this.target );
        renderer.render( this.renderScene, this.camera );


        this.fsQuad.material.uniforms.depthTexture.value = this.target.depthTexture;
        this.fsQuad.material.uniforms.colTexture.value = this.target.texture;
        

		// 2. Draw the outlines using the depth texture and normal texture
		// and combine it with the scene color
		if (this.renderToScreen) {
			// If this is the last effect, then renderToScreen is true.
			// So we should render to the screen by setting target null
			// Otherwise, just render into the writeBuffer that the next effect will use as its read buffer.
			renderer.setRenderTarget(null);
			this.fsQuad.render(renderer);
		} else {
			renderer.setRenderTarget(writeBuffer);
			this.fsQuad.render(renderer);
		}

	}

	createMaterial() {
		return new THREE.ShaderMaterial({
			uniforms: {
				depthTexture: {},
                colTexture: {},
			},
			vertexShader: CopyShader.vertexShader,
			fragmentShader: fragmentShader,
		});
	}
}

export { VisualizeDepthPass };