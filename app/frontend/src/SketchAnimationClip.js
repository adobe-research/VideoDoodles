import { DataTexture, Color } from "three";

import Stroke from './Stroke.js';

import { LogActionType, sessionLog } from './SessionLog.js';


export class SketchAnimationClip {
    constructor(nbFramesInVid) {
        this.frames = [
            {} // Dictionaries of strokes for all frames
        ];

        this.currentStrokeID = 0;

        this.startTime = 0;
        this.endTime = nbFramesInVid - 1;
        this.mode = "loop";
        this.padding = "hide";
        this.frameDuration = 4;
    }

    get N () { return this.frames.length; }

    getAnimationFrameIndexAt(t) {
        const N = this.frames.length;

        // Clamp to extreme frames
        if (t < this.startTime)
            return this.padding === "hide" ? -1 : 0;

        if (this.endTime !== undefined && t > this.endTime)
            return this.padding === "hide" ? -1 : N - 1;

        let frameIdx = Math.floor((t - this.startTime) / this.frameDuration);

        if (this.mode == "once") {
            return Math.max(0, Math.min(N - 1, frameIdx));
        }

        if (this.mode == "loop") {
            return Math.max(0, frameIdx % N);
        }
    }

    getNearestTimeForFrame(currentTime, targetFrameIdx) {
        const currentFrameIdx = this.getAnimationFrameIndexAt(currentTime);

        if (currentFrameIdx === targetFrameIdx)
            return currentTime;

        let targetTime = currentTime;
        if (this.mode == "loop") {
            let dF = targetFrameIdx - currentFrameIdx;
            if (currentTime < this.startTime) {
                currentTime = this.startTime;
                dF = targetFrameIdx;
            }
            if (currentTime > this.endTime) {
                currentTime = this.endTime;
                dF = targetFrameIdx - this.frames.length;
            }
            targetTime = currentTime + dF * this.frameDuration;

            if (targetTime < 0) {
                targetTime += this.N * this.frameDuration;
            }

            if (targetTime > this.endTime) {
                targetTime -= this.N * this.frameDuration;
            }
        }

        if (this.mode == "once") {
            targetTime = this.startTime + targetFrameIdx * this.frameDuration;
        }
        // let targetTime = this.startTime + targetFrameIdx * this.frameDuration;

        // if (targetFrameIdx < currentFrameIdx) {
        //     targetTime += this.frameDuration - 1;
        // }

        return targetTime;
    }

    setParameters(startTime, endTime, frameDuration) {
        this.startTime = startTime;
        this.endTime = endTime;
        this.frameDuration = frameDuration;
    }

    setMode(newMode) {
        this.mode = newMode;
    }

    setPadding(newPadding) {
        this.padding = newPadding;
    }

    // write(t, imageData) {
    //     // Replace the image at frame t by the current content of the canvas
    //     const frameIdx = this.getAnimationFrameIndexAt(t);

    //     console.log("writing frame " + frameIdx);

    //     this.frames[frameIdx] = imageData;

    // }

    getStrokes(t) {
        const frameIdx = this.getAnimationFrameIndexAt(t);
        if (frameIdx == -1)
            return {};
        const strokes = this.frames[frameIdx];

        return strokes;
    }

    renderStrokes(t, svg, interactable=true, color=undefined) {
        const strokes = this.getStrokes(t);
        // svg.selectAll("path").remove();
        Object.values(strokes).forEach(stroke => stroke.drawGizmo(svg, interactable, color));
    }

    renderStrokesAtFrame(frameIdx, svg, interactable, color=undefined) {
        const strokes = this.frames[frameIdx];
        // svg.selectAll("path").remove();
        Object.values(strokes).forEach(stroke => stroke.drawGizmo(svg, interactable, color));
    }

    renderOnionSkinning(t, svg) {
        const frameIdx = this.getAnimationFrameIndexAt(t);
        if (frameIdx - 1 >= 0) {
            // Render strokes from previous frame
            // console.log("rendering prev frame");
            this.renderStrokesAtFrame(frameIdx - 1, svg, false, "green");
        }

        if (frameIdx + 1 < this.frames.length) {
            // Render strokes from next frame
            // console.log("rendering next frame");
            this.renderStrokesAtFrame(frameIdx + 1, svg, false, "blue");
        }
    }

    createStroke(t, canvasID) {
        const frameIdx = this.getAnimationFrameIndexAt(t);
        const strokeID = this.currentStrokeID;
        const newStroke = new Stroke(strokeID, canvasID);
        this.currentStrokeID++;

        this.frames[frameIdx][strokeID] = newStroke;
        return strokeID;
    }

    addPointsToStroke( t, strokeId, pts ) {
        const frameIdx = this.getAnimationFrameIndexAt(t);
        this.frames[frameIdx][strokeId].addPoints(pts);
    }

    setStrokeColor( t, strokeId, color ) {
        const frameIdx = this.getAnimationFrameIndexAt(t);
        this.frames[frameIdx][strokeId].setColor(color);
    }

    setStrokeRadius( t, strokeId, radius ) {
        const frameIdx = this.getAnimationFrameIndexAt(t);
        this.frames[frameIdx][strokeId].setRadius(radius);
    }

    anySelected( t ) {
        const strokesAtT = this.getStrokes(t);
        const b = Object.values(strokesAtT).some((stroke) => {
            return stroke.selected;
        });
        return b;
    }

    deleteSelected( t ) {
        const strokesAtT = this.getStrokes(t);
        let strokesToRemove = [];
        Object.entries(strokesAtT).forEach(([key, stroke]) => {
            if (stroke.selected) {
                stroke.delete();
                strokesToRemove.push(key);
                sessionLog.log(LogActionType.StrokeDelete, {strokeID: stroke.strokeID, canvasID: stroke.canvasID})
            }
        });
        
        strokesToRemove.forEach( id => delete strokesAtT[id] );

    }

    delete() {
        this.frames.forEach((strokes) => {
            Object.values(strokes).forEach((s) => s.delete());
        })
    }

    renderAtTime(t, ctx) {
        // const ctx = canvas.getContext( '2d' );
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        // ctx.drawImage(this.frames[t], width, height);

        const frameIdx = this.getAnimationFrameIndexAt(t);
        this.renderFrame(frameIdx, ctx);
    }

    renderFrame(frameIdx, ctx) {
        const frame = this.frames[frameIdx];

        // createImageBitmap(frame).then((im) => {
        //     ctx.drawImage(im, 0, 0, frame.width, frame.height, 0, 0, ctx.canvas.width, ctx.canvas.height);
        // });
    }

    // getTextureAtFrame(t) {
    //     const frameIdx = this.getAnimationFrameIndexAt(t);
    //     console.log("reading frame " + frameIdx);


    //     // Get the Uint8ClampedArray data
    //     const d = this.frames[frameIdx];

    //     console.log("getTextureAtFrame");
    //     console.log(d);

    //     const tex = new DataTexture(d, this.width, this.height);
    //     tex.flipY = true;
        
    //     return tex;
    // }

    addFrame(time, copy=true) {
        const frameIdx = this.getAnimationFrameIndexAt(time);

        // if (copy)
        //     this.frames.push(new ImageData(this.frames[this.frames.length - 1].data, this.width, this.height));
        // else
        //     this.frames.push(new ImageData(width, height));

        this.frames.splice(frameIdx + 1, 0, {});

        sessionLog.log(LogActionType.FrameCreate, {}, false);

        // Return new frame ID
        return frameIdx + 1;

    }

    deleteFrame(frameIdx) {
        // Don't delete if there is only 1 frame left
        if (this.frames.length <= 1)
            return;
        const strokesToDelete = this.frames[frameIdx];
        Object.values(strokesToDelete).forEach((s) => s.delete());

        this.frames.splice(frameIdx, 1);
    }

    changeFrameIdx(source, target) {
        const newFramesList = this.frames;

        if (source < target) {
            newFramesList.splice(target + 1, 0, newFramesList[source]);
            newFramesList.splice(source, 1);
        } 
        else {
            newFramesList.splice(target, 0, newFramesList[source]);
            newFramesList.splice(source + 1, 1);
        }

        this.frames = newFramesList;
    }

    export() {
        let framesExport = this.frames.map((frame) => {
            let strokes = Object.values(frame);
            return strokes.map((s) => s.export());
        });

        return {
            "frames": framesExport,
            "startTime": this.startTime,
            "endTime": this.endTime,
            "mode": this.mode,
            "padding": this.padding,
            "frameDuration": this.frameDuration,
        }
    }

    loadFrames(framesData) {
        let maxStrokeID = -1;
        this.frames = framesData.map((d) => {
            let fr = {};
            d.forEach((strokeData) => {
                maxStrokeID = Math.max(maxStrokeID, strokeData.strokeID);
                let newStroke = new Stroke(strokeData.strokeID, strokeData.canvasID);
                newStroke.geometry.setPositions(strokeData.points);
                newStroke.setColor(new Color(strokeData.color.x, strokeData.color.y, strokeData.color.z));
                newStroke.setRadius(strokeData.radius);

                // console.log(newStroke.geometry);

                fr[strokeData.strokeID] = newStroke;
            })
            return fr;
        })

        this.currentStrokeID = maxStrokeID + 1;
    }
}