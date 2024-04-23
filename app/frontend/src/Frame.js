import { PerspectiveCamera, Matrix4, Vector2, Vector3, Vector4, NearestFilter } from "three";

export default class Frame {
    constructor(time, rawCameraData) {
        this.time = time;

        this.depth = undefined;

        this.setCamera(rawCameraData);
    }

    setCamera(rawCameraData) {
        
        const cameraData = rawCameraData; 

        let camera = new PerspectiveCamera();

        // cameraData['cameraProjectionTransform'][10] = 
        camera.projectionMatrix.set(...cameraData['cameraProjectionTransform']);
        camera.projectionMatrixInverse.copy( camera.projectionMatrix ).invert();

        camera.matrixWorld = new Matrix4();

        camera.position.set(
            cameraData['translation'][0],
            cameraData['translation'][1],
            cameraData['translation'][2]
        );

        camera.quaternion.set(
            cameraData['rotation'][0],
            cameraData['rotation'][1],
            cameraData['rotation'][2],
            cameraData['rotation'][3]
        );


        camera.matrixAutoUpdate = true;
        camera.updateMatrixWorld();

        camera.matrixWorldInverse.copy( camera.matrixWorld ).invert();

        camera.matrixAutoUpdate = false;
        
        this.camera = camera;
        this.cameraData = cameraData;

        
    }

    setDepth(depth) {
        this.depth = depth;
        this.depth.magFilter = NearestFilter;
        this.depth.minFilter = NearestFilter;
    }

    dispose() {
        this.depth.dispose();
        this.depth = undefined;
    }

    getNearFar() {
        
        // console.log(this.cameraData['cameraProjectionTransform'][0]);
        let m22 = this.cameraData['cameraProjectionTransform'][10];
        let m32 = this.cameraData['cameraProjectionTransform'][11];
        // console.log("m22 = " + m22 + ", m32 = " + m32)
        let near = (2.0 * m32)/(2.0 * m22-2.0);
        let far = ((m22-1.0)*near)/(m22+1.0);
        // let far = 10000;

        console.log(`near ${near}, far ${far}`);

        return { near, far};
        
    }


    getVP() {
        const vp = new Matrix4();
        vp.multiplyMatrices(this.camera.projectionMatrix ,this.camera.matrixWorldInverse);
        return vp;
    }

    // Note: this returns normalized coordinates!
    project(pt) {
        // if (!this.loaded)
        //     return new Vector2();

        let newPt = pt.clone();
        newPt.project(this.camera);
        let x = ( newPt.x + 1) / 2;
        let y = - ( newPt.y - 1) / 2;
        return new Vector2(x, y);
    }

    getDepth(pt) {
        // Return depth as distance along view axis from camera to point
        // let localPt = this.worldToLocal(pt);
        let localPt = pt.clone();
        localPt.project(this.camera);
        return localPt.z;
    }

    convertToLocalRotation(mat) {
        const localMat = new Matrix4();
        const rotMat = new Matrix4();
        rotMat.extractRotation(this.camera.matrixWorld);
        localMat.multiplyMatrices(mat, rotMat);
        return localMat;
    }

    convertToWorldRotation(mat) {
        const worldMat = new Matrix4();
        const inverseRotMat = new Matrix4();
        inverseRotMat.extractRotation(this.camera.matrixWorldInverse);
        worldMat.multiplyMatrices(mat, inverseRotMat);
        return worldMat;
    }

    worldToLocal(pt) {
        let worldPt = pt.clone();
        worldPt.applyMatrix4(this.camera.matrixWorldInverse);
        return worldPt;
    }

    localToWorld(pt) {
        let localPt = pt.clone();
        localPt.applyMatrix4(this.camera.matrixWorld);
        return localPt;
    }

    projectLocal(pt) {
        let proj = pt.clone();
        proj.applyMatrix4( this.camera.projectionMatrix );
        let x = ( proj.x + 1) / 2;
        let y = - ( proj.y - 1) / 2;
        return new Vector2(x, y);
    }

    getViewDirection() {
        const viewDir = new Vector3();
        this.camera.getWorldDirection(viewDir);

        return viewDir;
    }

    // Returns a vector4 of the point in clip space BEFORE perspective division (w != 1)
    worldToClip(pt) {
        let pt4 = new Vector4(pt.x, pt.y, pt.z, 1.0);
        let proj = pt4.applyMatrix4( this.camera.matrixWorldInverse ).applyMatrix4( this.camera.projectionMatrix );
        return proj;
    }

    moveOnScreen(originalPos, target2D) {
        // Move the original position such that it reprojects to the target 2D position (in normalized [0, 1] coords)
        // The depth stays the same
        let targetX = target2D.x * 2 - 1;
        let targetY = -target2D.y * 2 + 1;

        let newPt = new Vector3(targetX, targetY, this.getDepth(originalPos));
        newPt.applyMatrix4( this.camera.projectionMatrixInverse );
        newPt.applyMatrix4(this.camera.matrixWorld);
        return newPt;
    }

    screenSpaceToWorldSpace(x, y, depth) {
        const unproj = new Vector3();
        unproj.x = x * 2 - 1;
        unproj.y = -y * 2 + 1;

        if (depth) {
            unproj.z = depth;
        }
        else {
            unproj.z = 0;
        }

        // unproj.unproject(this.camera);
        unproj.applyMatrix4( this.camera.projectionMatrixInverse );
        unproj.applyMatrix4(this.camera.matrixWorld);

        return unproj;
    }
}