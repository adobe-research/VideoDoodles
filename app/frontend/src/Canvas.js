import { Matrix4, Vector2, Vector3, BufferAttribute, BufferGeometry, Float32BufferAttribute, Mesh, ShaderMaterial, CanvasTexture, PlaneGeometry, MeshBasicMaterial, DoubleSide, Object3D } from 'three';

import vertexShader from './shaders/canvasVertex.glsl';
import fragmentShader from './shaders/canvasFragment.glsl';

import { generateGridGeometry } from './vertexGrid';


const viewPlaneMat = new ShaderMaterial({
    uniforms :{
        pos: { value: new Vector3() },
        rot: { value: new Matrix4() },
        scale: { value: 1.0 },
        worldSpace: { value: true },
        tex: { value: undefined },
        opacity: { value: 1.0 },
        backgroundColor: {value: new Vector3(1, 1, 1)},
        debug: { value: true },
        backgroundOpacity: { value: 0.5 },
    },
    vertexShader : vertexShader,
    fragmentShader : fragmentShader,
    side: DoubleSide,
    transparent: true,
    depthWrite: false
    // wireframe: true
    // alphaTest: 0.8
});

export const gridN = 2;


export default class Canvas {
    constructor() {
        this.ID = -1; // The ID corresponds to the animated canvas ID set by the animation controller
        this.position = new Vector3();
        this.scale = 1.0;
        this.rotation = new Matrix4();

        this.worldSpace = true;

        const viewPlaneGeom = generateGridGeometry(gridN - 1);

        // Copying shader so that we can change uniforms
        this.material = viewPlaneMat.clone();

        this.object = new Mesh( viewPlaneGeom, this.material );
        // this.object.renderOrder = 5;

        // This is essential, otherwise the plane will sometimes get culled!
        this.object.frustumCulled = false;

        this.strokesContainer = new Object3D();

        this.object.add(this.strokesContainer);

    }

    getObject() { return this.object; }

    updateStrokes(strokes) {
        this.strokesContainer.clear();
        Object.values(strokes).forEach( stroke => {
            stroke.addTo(this.strokesContainer);
            stroke.setCanvasPosition(this.position);
            stroke.setCanvasRotation(this.rotation);
            stroke.setCanvasScale(this.scale);
        })
    }


    setPosition(posVec) {
        this.position = posVec;
        this.material.uniforms.pos.value = posVec;
    }

    setDrawingOpacity(o) {
        this.material.uniforms.opacity.value = o;
    }

    setBackgroundOpacity(o) {
        this.material.uniforms.backgroundOpacity.value = o;
    }

    setBackgroundColor(c) {
        this.material.uniforms.backgroundColor.value = c;
    }

    setDebugView(b) {
        this.material.uniforms.debug.value = b;
    }

    setRotation(rotMat) {
        this.rotation = rotMat;
        this.material.uniforms.rot.value = rotMat;
    }


    setZ(z) {
        this.position.setComponent(2, z);
        this.material.uniforms.pos.value = this.position;
    }

    setScale(s) {
        this.scale = s;
        this.material.uniforms.scale.value = this.scale;
    }

    setSpace(isWorldSpace) {
        this.worldSpace = isWorldSpace;
        this.material.uniforms.worldSpace.value = this.worldSpace;
    }

    delete() {
        this.object.geometry.dispose();
        if (this.material.uniforms.tex.value)
            this.material.uniforms.tex.value.dispose();
        this.material.dispose();
    }

}