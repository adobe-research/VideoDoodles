import { Vector3, Vector2, Matrix4, Vector4, Euler } from 'three';
import { derived, get, writable } from 'svelte/store';

import { CanvasGizmo } from './CanvasGizmo.js';
import { Keyframe } from './Keyframe.js';

import { send } from './websocket.js';

import { clipFrames, clipName, time as appTime } from './store.js';
import { SketchAnimationClip } from './SketchAnimationClip.js';

import { LogActionType, sessionLog } from './SessionLog.js';

const InterpolationModes = {
    Linear: 0,
    Tracking: 1,
}

class TrajectorySegment {
    constructor(timeStart, timeEnd, interpMode) {
        this.start = timeStart;
        this.end = timeEnd;

        this.mode = interpMode;
        this.dirty = true;
    }

    get ID() {
        return `${this.start}-${this.end}`;
    }

    contains(time) {
        return time >= this.start && time <= this.end;
    }

    setLinear() {
        if (this.mode !== InterpolationModes.Linear)
            this.dirty = true;
        this.mode = InterpolationModes.Linear;
    }

    setTracking() {
        if (this.mode !== InterpolationModes.Tracking)
            this.dirty = true;
        this.mode = InterpolationModes.Tracking;
    }

    toString() {
        return `${this.start + 1} - ${this.end + 1}`;
    }

    markClean() {
        this.dirty = false;
    }

    markDirty() {
        this.dirty = true;
    }

    export() {
        return {
            start: this.start,
            end: this.end,
            mode: this.mode,
            dirty: this.dirty
        }
    }

}

export class AnimatedCanvas {
    constructor(canvas, trajectory) {
        this.canvas = canvas;
        
        // Data
        this.trajectory = trajectory;

        // User given constraints
        this.init();

        this.gizmo = new CanvasGizmo(this);
        this.type = "static";

        this.animationClip = new SketchAnimationClip(get(clipFrames).length);
        
        // this.hasDirtyKeyframes = false;
        this.trajectoryUpToDate = true;
    }

    init() {
        this.keyframes = {};

        const fullSegmentPos = new TrajectorySegment(0, this.trajectory.length - 1, InterpolationModes.Tracking);
        this.positionSegments = {};
        this.positionSegments[fullSegmentPos.ID] = fullSegmentPos;
        fullSegmentPos.markClean();

        const fullSegmentRot = new TrajectorySegment(0, this.trajectory.length - 1, InterpolationModes.Tracking);
        this.orientationSegments = {};
        this.orientationSegments[fullSegmentRot.ID] = fullSegmentRot;
        fullSegmentRot.markClean();
    }

    get ID() {
        return this.canvas.ID;
    }

    get hasDirtySegments() {
        return this.getKeyframedSegments(this.positionSegments, "x").some((s) => s.dirty) || this.getKeyframedSegments(this.orientationSegments, "rot").some((s) => s.dirty) ;
    }

    getPosition(time) {
        return this.trajectory[time].position;
    }

    getRotation(time) {
        return this.trajectory[time].rotation;
    }

    getNormal(time, screenSpace=false) {
        const worldNormal = new Vector4(0, 0, 1, 0);
        worldNormal.applyMatrix4(this.getRotation(time));
        if (screenSpace) {
            const frame = get(clipFrames)[time];

            // If the normal is facing away from the camera, take the inverse vector
            if (frame.worldToLocal(worldNormal).z < 0) {
                // console.log("facing away")
                worldNormal.negate();
            }

            // const pos = this.getCurrentPosition(false);
            const pos = this.getPosition(time).clone();
            pos.add(worldNormal);

            // Compute screen space norm of a screen aligned unit vector at this position
            const posExtreme = this.getPosition(time).clone();
            posExtreme.add(frame.localToWorld(new Vector4(1, 0, 0, 0)));

            const projectedExtremeVec = frame.project(posExtreme).sub(this.getProjectedPosition(time));
            // console.log(projectedExtremeVec)
            // projectedExtremeVec.setY(projectedExtremeVec.y * frame.getAspectRatio())

            const lengthExtreme = (new Vector2(projectedExtremeVec.x, projectedExtremeVec.y)).length();

            // const projectedNormal2D = frame.project(pos).sub(this.getCurrentPosition(true));
            const projectedNormal2D = frame.project(pos).sub(this.getProjectedPosition(time));
            // projectedExtremeVec.setX(projectedNormal2D.x * frame.getAspectRatio())

            projectedNormal2D.divideScalar(lengthExtreme);

            return projectedNormal2D;
        }
        else
            return worldNormal;
    }

    getDepth(time) {
        let depth = get(clipFrames)[time].getDepth(this.getPosition(time));
        return depth
    }

    getProjectedPosition(time, frame, clamp=false) {
        if (frame === undefined)
            frame = get(clipFrames)[time];

        let pos = frame.project(this.getPosition(time));

        // If canvas is not visible in screen, clamp
        if (clamp) {
            pos.x = Math.max(Math.min(pos.x, 1), 0);
            pos.y = Math.max(Math.min(pos.y, 1), 0);
        }
        return pos;
    }

    getProjectedDepth(time, frame) {
        if (frame === undefined)
            frame = get(clipFrames)[time];

        let depth = frame.getDepth(this.getPosition(time));

        return depth;
    }

    getProjectedRotation(time) {
        const frame = get(clipFrames)[time];
        return frame.convertToLocalRotation(this.canvas.rotation);
    }

    getProjectedOrientation(time) {
        // const time = get(appTime);
        const rotMat = this.getRotation(time);
        const up = new Vector4(0, 1, 0, 0);
        up.applyMatrix4(rotMat);
        const localUp = get(clipFrames)[time].worldToLocal(up);
        
        const right = new Vector4(1, 0, 0, 0);
        right.applyMatrix4(rotMat);
        const localRight = get(clipFrames)[time].worldToLocal(right);

        return {reverseY: localUp.y < 0, reverseX: localRight.x < 0};
    }

    getProjectedSkewness(time, resX, resY) {
        const frame = get(clipFrames)[time];

        let centerPos = this.getPosition(time).clone();
        let xVec = new Vector4(this.canvas.scale, 0, 0, 0);
        xVec.applyMatrix4(this.getRotation(time));

        let yVec = new Vector4(0, this.canvas.scale, 0, 0);
        yVec.applyMatrix4(this.getRotation(time));

        let br = centerPos.clone();
        br.add(xVec);
        let brProj = frame.project(br);

        let tr = centerPos.clone();
        tr.add(yVec);
        let trProj = frame.project(tr);
        let centerProj = frame.project(centerPos);

        let xVecProj = brProj.clone();
        xVecProj.sub(centerProj);
        xVecProj.multiply(new Vector2(resX, resY));
        // xVecProj = xVecProj.normalize();

        let yVecProj = trProj.clone();
        yVecProj.sub(centerProj);
        yVecProj.multiply(new Vector2(resX, resY));

        // yVecProj = yVecProj.normalize();

        // console.log(xVecProj.length());
        // console.log(yVecProj.length());

        // skewRatio = Math.abs(xVecProj.dot(yVecProj))

        // console.log("dot product " + xVecProj.dot(yVecProj));

        let xVecScreen = frame.worldToLocal(centerPos).add(new Vector4(this.canvas.scale, 0, 0, 0));
        let xVecScreenProj = frame.projectLocal(xVecScreen);
        xVecScreenProj.sub(centerProj);
        xVecScreenProj.multiply(new Vector2(resX, resY));

        let yVecScreen = frame.worldToLocal(centerPos).add(new Vector4(0, this.canvas.scale, 0, 0));
        let yVecScreenProj = frame.projectLocal(yVecScreen);
        yVecScreenProj.sub(centerProj);
        yVecScreenProj.multiply(new Vector2(resX, resY));

        // console.log("cross ? " + (xVecProj.cross(yVecProj) / (resX * resY)) );
        // console.log("cross base ? " + (xVecScreenProj.cross(yVecScreenProj) / (resX * resY)) );

        // console.log("ratio" + (xVecProj.cross(yVecProj) / xVecScreenProj.cross(yVecScreenProj)));

        let skewness = 1.0 - Math.min(1.0, Math.abs((xVecProj.cross(yVecProj) / xVecScreenProj.cross(yVecScreenProj))));
        
        // let skewness = Math.abs(xVecProj.length() - yVecProj.length()) / Math.max(xVecProj.length(), yVecProj.length());
        // console.log(skewness);

        // Check if out of screen
        if (centerProj.x < 0 || centerProj.y < 0 || centerProj.x > 1 || centerProj.y > 1)
            skewness = 1;

        return skewness;

    }

    select() {
        this.gizmo.select();
        this.canvas.setBackgroundOpacity(0.5);
    }

    unselect() {
        this.gizmo.unselect();
        this.canvas.setBackgroundOpacity(0.0);
    }

    drawFromCanvas(time, context2D) {
        return this.animationClip.renderAtTime(time, context2D)
    }

    // drawToCanvas(time, context2D) {
    //     this.animationClip.write(time, context2D);
    //     this.canvas.setTexture(this.animationClip.getTextureAtFrame(time));
    // }

    createStroke(time) {
        const newStrokeID = this.animationClip.createStroke(time, this.ID);
        // Update canvas' strokes
        this.canvas.updateStrokes(this.animationClip.getStrokes(time));
        return newStrokeID;
    }

    addPointsToStroke(time, strokeID, pts) {
        this.animationClip.addPointsToStroke(time, strokeID, pts);
        // this.canvas.updateStrokes(this.animationClip.getStrokes(time));
    }

    setStrokeColor(time, strokeID, color) {
        this.animationClip.setStrokeColor(time, strokeID, color);
    }

    setStrokeRadius(time, strokeID, radius) {
        // Convert canvas NDC space radius to the corresponding clip space radius at the corresponding 3D position of the canvas at the time of drawing
        const frame = get(clipFrames)[time];
        // const canvasW = frame.worldToClip(this.getPosition(time)).w;

        // const {near, far} = frame.getNearFar();
        // console.log(frame.camera.projectionMatrix);
        // console.log("scale factor " + (far - near));
        let clipSpaceRadius = this.canvas.scale * radius * frame.camera.projectionMatrix.elements[5] * 2;
        this.animationClip.setStrokeRadius(time, strokeID, clipSpaceRadius);
        // this.animationClip.setStrokeRadius(time, strokeID, radius);
    }

    renderStrokes(time, svg, interactable=true) {
        this.animationClip.renderStrokes(time, svg, interactable);
    }

    renderOnionSkinning(time, svg) {
        this.animationClip.renderOnionSkinning(time, svg);
    }

    deleteSelectedStrokes(time) {
        this.animationClip.deleteSelected(time);
    }

    addFrame(time) {
        const newFrameIdx = this.animationClip.addFrame(time);
        return newFrameIdx;
    }

    setTime(time) {
        // Change canvas properties to reflect the trajectory at given frame
        let currentPos = this.getPosition(time);
        // console.log(currentPos);
        // console.log(this.getRotation(time));
        this.canvas.setPosition(currentPos);
        this.canvas.setRotation(this.getRotation(time));

        // Commented for debug trajectory vis
        this.updateStrokes(time);

        // // Debug vis
        // if (this.isKeyframed(time, "x")) {
        //     if (this.isKeyframed(time, "rot"))
        //         this.canvas.setBackgroundColor(new Vector3(0.87058824, 0.17647059, 0.1490196));
        //     else
        //         this.canvas.setBackgroundColor(new Vector3(0.17254902, 0.63529412, 0.37254902));
        // }
        // else {
        //     if (this.isKeyframed(time, "rot"))
        //         this.canvas.setBackgroundColor(new Vector3(0.19215686, 0.50980392, 0.74117647));
        //     else
        //         this.canvas.setBackgroundColor(new Vector3(1, 1, 1));
        // }

        // this.canvas.setTexture(this.animationClip.getTextureAtFrame(time));

    }

    updateStrokes(time) {
        // Change which frame of the animation clip is being displayed
        this.canvas.updateStrokes(this.animationClip.getStrokes(time));
    }

    setType(type) {
        if (this.type !== type.toLowerCase()) {
            sessionLog.log(LogActionType.CanvasSetType, {canvasID: this.ID, type: type.toLowerCase()})
            // If static type: remove all keyframes
            if (type.toLowerCase() === "static") {
                this.init();
                // console.log(this.positionSegments);
                // console.log(this.orientationSegments);
                this.type = type.toLowerCase();

                // Always need to have one position keyframe!
                this.addKeyframe(get(appTime), {"x": 0.5, "y": 0.5})

                return;
            }
        }


        this.type = type.toLowerCase();

        // Mark all segments as dirty
        Object.values(this.positionSegments).forEach((s) => {
            s.markDirty();
        })

        Object.values(this.orientationSegments).forEach((s) => {
            s.markDirty();
        })


        // if (Object.values(this.keyframes).length > 0)
        //     this.hasDirtyKeyframes = true;

    }

    getKeyframedSegments(segments, prop) {
        return Object.values(segments).filter((s) => this.isKeyframed(s.start, prop) || this.isKeyframed(s.end, prop));
    }
    
    getPositionSegment(time) {
        const segment = Object.values(this.positionSegments).find((segment) => segment.contains(time));
        // Only return if either start or end is keyframed
        if (segment && (this.isKeyframed(segment.start, "x") || this.isKeyframed(segment.end, "x")))
            return segment;

        return undefined;
    }

    getOrientationSegment(time) {
        const segment = Object.values(this.orientationSegments).find((segment) => segment.contains(time));
        // Only return if either start or end is keyframed
        if (segment && (this.isKeyframed(segment.start, "rot") || this.isKeyframed(segment.end, "rot")))
            return segment;

        return undefined;
    }

    splitSegment(segments, time) {
        // Update trajectory segments
        // Find old segment
        let containingSegments = Object.values(segments).filter((segment) => segment.contains(time));
        if (containingSegments.length == 1) {
            let containingSegment = containingSegments[0];
            if (containingSegment.start == time || containingSegment.end == time) {
                // Don't split but mark as dirty
                containingSegment.markDirty();
                return;
            }
            // Split into max 2 new segments
            if (time - containingSegment.start > 0) {
                const lSegment = new TrajectorySegment(containingSegment.start, time, containingSegment.mode);
                segments[lSegment.ID] = lSegment;
            }
            if (containingSegment.end - time > 0) {
                const rSegment = new TrajectorySegment(time, containingSegment.end, containingSegment.mode);
                segments[rSegment.ID] = rSegment;
            }
            delete segments[containingSegment.ID];
        }
        else if (containingSegments.length == 2) {
            // time is at an existing keyframe, mark both segments as dirty, don't split
            containingSegments.forEach((s) => s.markDirty())
        }
        else {
            console.error(`Can't split segments at ${time}: no segment contains this time.`);
        }
    }

    mergeSegments(segments, time) {
        let lSegment = Object.values(segments).find((segment) => segment.end == time);
        let rSegment = Object.values(segments).find((segment) => segment.start == time);

        let remainingSegment;

        if (lSegment && rSegment) {
            // Merge
            remainingSegment = new TrajectorySegment(lSegment.start, rSegment.end, lSegment.mode);
            segments[remainingSegment.ID] = remainingSegment;

            delete segments[lSegment.ID];
            delete segments[rSegment.ID];
        }
        else {
            if (lSegment) {
                lSegment.markDirty();
                remainingSegment = lSegment
            }
            else if (rSegment) {
                rSegment.markDirty();
                remainingSegment = rSegment
            }
        }

        return remainingSegment;

    }

    addKeyframe(time, props) {
        // If a keyframe already exists at this time, we merge the new properties
        let newKeyframe;
        if (this.keyframes.hasOwnProperty(time)) {
            newKeyframe = this.keyframes[time];
            Object.keys(props).forEach((k) => newKeyframe.addProperty(k, props[k]));
            // Object.assign(newKeyframe.props, props);
        }
        else {
            newKeyframe = new Keyframe(time, props);
            this.keyframes[time] = newKeyframe;
            
        }
        console.log("Canvas " + this.canvas.ID + " keyframes: " + this.keyframes);

        // If this is a static canvas, prevent multiple keyframing of position
        if (this.type === "static") {
            if ("x" in props || "y" in props || "depth" in props) {
                let otherKeyframedTimes = Object.keys(this.keyframes).filter((t) => t != time);
                otherKeyframedTimes.forEach((t) => this.removeKeyframeProps(t, ["x", "y", "depth"]));
            }
        }

        // console.log(this.positionSegments);

        // Update trajectory segments
        if ("x" in props || "y" in props || "depth" in props) {
            this.splitSegment(this.positionSegments, time);
        }
        if ("rot" in props) {
            this.splitSegment(this.orientationSegments, time);
        }
        
        // console.log(this.orientationSegments);

        // Set trajectory position to match the keyframe
        const frame = get(clipFrames)[time];
        let depth = frame.getDepth(this.trajectory[time].position);
        if ("depth" in props) {
            depth = props.depth;
        }
        if ("x" in props && "y" in props) {
            const newPos = frame.screenSpaceToWorldSpace(props.x, props.y, depth);
            this.trajectory[time].position = newPos;
        }
        
        if ("rot" in props) {
            // const newRotMat = frame.convertToWorldRotation(props["rot"]);
            // console.log(props["rot"]);
            // console.log(newRotMat);
            this.trajectory[time].rotation = props["rot"];
            newKeyframe.addProperty("rot", props["rot"]);
        }

        // if ("scale" in props) {
        //     this.canvas.setScale(props["scale"]);
        //     console.log("scale update")
        // }


        this.setTime(time);

        // this.hasDirtyKeyframes = true;

        return newKeyframe;
    }

    removeKeyframeProps(time, props) {
        // Forbid removing x, y without removing depth
        if (props.includes("x")) {
            if (!props.includes("depth")) props.push("depth");
        }

        if (this.keyframes.hasOwnProperty(time)) {
            const kf = this.keyframes[time];

            // Forbid removing the last position keyframe of a canvas
            if (this.getKeyframes().length == 1) {
                console.log("Can't remove last position keyframe of a canvas.")
                props = props.filter(prop => prop !== "x" && prop !== "y")
            }

            
            let propWasRemoved = {}
            props.map((k) => {
                let r = kf.removeProperty(k);
                propWasRemoved[k] = r;
            });

            // console.log(props);

            // Update trajectory segments
            // Merge position segments only if all properties have been removed
            if (propWasRemoved["x"] && propWasRemoved["y"] && !kf.hasProperty("depth")) {
                // if (!kf.hasProperty("depth")) {
                    // console.log(this.positionSegments);
                    // console.log(time)
                    let s = this.mergeSegments(this.positionSegments, time);
                    if (!this.isKeyframed(s.start, "x") && !this.isKeyframed(s.end, "x")) {
                        s.setTracking();
                    }
                // }
                // else {
                //     // Mark segments as dirty
                //     let lSegment = Object.values(this.positionSegments).find((segment) => segment.end == time);
                //     let rSegment = Object.values(this.positionSegments).find((segment) => segment.start == time);
                //     if (lSegment) lSegment.markDirty();
                //     if (rSegment) rSegment.markDirty();
                // }
            }
            // If we are only removing depth (and NOT x and y)
            else if (propWasRemoved["depth"]) {
                if (!kf.hasProperty("x")) {
                    let s = this.mergeSegments(this.positionSegments, time);
                    if (!this.isKeyframed(s.start, "x") && !this.isKeyframed(s.end, "x")) {
                        s.setTracking();
                    }
                }
                else {
                    // Mark segments as dirty
                    let lSegment = Object.values(this.positionSegments).find((segment) => segment.end == time);
                    let rSegment = Object.values(this.positionSegments).find((segment) => segment.start == time);
                    if (lSegment) lSegment.markDirty();
                    if (rSegment) rSegment.markDirty();
                }
            }

            if (props.includes("rot")) {
                let s = this.mergeSegments(this.orientationSegments, time);
                if (!this.isKeyframed(s.start, "rot") && !this.isKeyframed(s.end, "rot")) {
                    s.setTracking();
                }
            }

            sessionLog.log(LogActionType.KeyframeRemove, {
                canvasID: this.ID,
                keyframeTime: kf.time,
                editedProps: props
            })

            // Should we just delete this keyframe?
            if (kf.isEmpty())
                this.clearKeyframe(time);
            // Object.assign(newKeyframe.props, props);
            // this.hasDirtyKeyframes = true;
        }
    }

    exportKeyframes() {
        send({
            "action": "EXPORT_KEYFRAMES",
            "canvasID": this.ID,
            "keyframes": this.getKeyframes(),
            "positionSegments": Object.values(this.positionSegments),
            "orientationSegments": Object.values(this.orientationSegments),
            "clip": get(clipName),
            "type": this.type,
        });
    }

    inferTrajectory() {

        sessionLog.log(LogActionType.TrajectoryInfer, {
            canvasID: this.ID,
            keyframes: this.getKeyframes().map((k) => k.export()),
            positionSegments: Object.values(this.positionSegments).map((s) => s.export()),
            orientationSegments: Object.values(this.orientationSegments).map((s) => s.export()),
            type: this.type
        }, false) // Allow for duplicates in log (deep objects)

        send({
            "action": "INFER_TRAJECTORY",
            "canvasID": this.ID,
            "keyframes": this.getKeyframes(),
            "positionSegments": Object.values(this.positionSegments),
            "orientationSegments": Object.values(this.orientationSegments),
            "clip": get(clipName),
            "type": this.type,
        });

        this.markTrajectoryPoints(false, false);

        // this.getKeyframes().forEach((kf) => {
        //     if (kf.props.hasOwnProperty("depth")) {
        //         const pos3D = get(clipFrames)[kf.time].screenSpaceToWorldSpace(kf.props.x, kf.props.y, kf.props.depth)
        //         console.log("kf " + kf.time + " pos " + pos3D.x + " " + pos3D.y + " " + pos3D.z);
        //         console.log(this.trajectory[kf.time].position);
        //     }
        // })

        // animationController.updateCanvases();

        // this.hasDirtyKeyframes = false;
        // this.trajectoryUpToDate = false;
        
    }

    applyInferredTrajectory(positions, rotations, indices) {

        indices.forEach((frameIdx, idx) => {
            if (positions != undefined) {
                this.trajectory[frameIdx].position = positions[idx];
                this.trajectory[frameIdx].positionSolved = true;

                // Mark segments as clean
                Object.values(this.positionSegments).forEach((s) => { if (s.contains(frameIdx)) s.markClean()});
            }
            if (rotations != undefined) {
                this.trajectory[frameIdx].rotation = rotations[idx];
                this.trajectory[frameIdx].rotationSolved = true;

                // Mark segments as clean
                Object.values(this.orientationSegments).forEach((s) => { if (s.contains(frameIdx)) s.markClean()});
            }


        })

        this._setUpToDate();
    }

    // applyInferredDepthOffsets(depthOffsets) {
    //     this.depthOffsets.values = depthOffsets;
    // }

    markTrajectoryPoints(positionSolved, rotationSolved, indices=undefined) {
        if (indices == undefined) {
            this.trajectory.forEach((pt) => {
                if (positionSolved !== undefined)
                    pt.positionSolved = positionSolved;
                if (rotationSolved !== undefined)
                    pt.rotationSolved = rotationSolved;
            });
        }

        else {
            indices.forEach((frameIdx) => {
                if (positionSolved !== undefined)
                    this.trajectory[frameIdx].positionSolved = positionSolved;
                if (rotationSolved !== undefined)
                this.trajectory[frameIdx].rotationSolved = rotationSolved;
            });
        }
        this._setUpToDate();
    }

    _setUpToDate() {
        const isNowUpToDate = this.trajectory.every((pt) => {
                return pt.solved;
            }
        )

        if (!this.trajectoryUpToDate && isNowUpToDate) {
            sessionLog.log(LogActionType.TrajectorySolved, {
                canvasID: this.ID
            })
        }

        this.trajectoryUpToDate = isNowUpToDate;
    }

    clearKeyframe(time) {
        if (this.keyframes.hasOwnProperty(time)) {
            this.keyframes[time].clear();
            delete this.keyframes[time];
            // this.hasDirtyKeyframes = true;
        }
    }

    getKeyframes() {
        return Object.values(this.keyframes);
    }

    isKeyframed(time, prop) {
        return this.keyframes.hasOwnProperty(time) && this.keyframes[time].hasProperty(prop);
    }

    delete() {
        this.canvas.delete();
        this.gizmo.delete();
        this.animationClip.delete();
    }

    export() {
        return {
            "canvasID": this.ID,
            "trajectory": this.trajectory.map(pt => pt.export()),
            "scale": this.canvas.scale,
            "keyframes": this.getKeyframes(),
            "positionSegments": Object.values(this.positionSegments),
            "orientationSegments": Object.values(this.orientationSegments),
            "animationClip": this.animationClip.export(),
            // "clip": get(clipName),
            "type": this.type,
        }
    }

    loadKeyframes(keyframesData) {
        this.keyframes = {};

        keyframesData.forEach((kf) => {
            this.keyframes[kf.time] = new Keyframe(kf.time, kf.props);
        })
    }

    loadSegments(positionSegments, orientationSegments) {
        this.positionSegments = {};
        this.orientationSegments = {};

        positionSegments.forEach((s) => {
            let segmentObj = new TrajectorySegment(s.start, s.end, s.mode == 0 ? InterpolationModes.Linear : InterpolationModes.Tracking);
            segmentObj.markClean();
            this.positionSegments[segmentObj.ID] = segmentObj;
        });

        orientationSegments.forEach((s) => {
            let segmentObj = new TrajectorySegment(s.start, s.end, s.mode);
            segmentObj.markClean();
            this.orientationSegments[segmentObj.ID] = segmentObj;
        });
    }

    loadAnimationClip(data) {
        this.animationClip = new SketchAnimationClip(data.endTime + 1);
        this.animationClip.setParameters(data.startTime, data.endTime, data.frameDuration);
        this.animationClip.setMode(data.mode);
        this.animationClip.setPadding(data.padding);
        this.animationClip.loadFrames(data.frames);
    }


}