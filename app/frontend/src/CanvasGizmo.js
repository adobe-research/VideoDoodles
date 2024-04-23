import { Vector3, Vector2, Matrix4, Vector4, Euler } from 'three';
import { derived, get, writable } from 'svelte/store';
import * as d3 from "d3";

import { clipFrames, time as appTime } from './store.js';
import { animationController } from "./AnimationController.js";

import { LogActionType, sessionLog } from './SessionLog.js';


const gizmoDim = new Vector2(50, 50);
const hintArrowDim = 30;


function projectedNormalToRotation(projectedNormalVec, originalZRot, reverseX, reverseY) {

    let rotX = 0.5 * Math.PI * projectedNormalVec.y;
    let rotY = -0.5 * Math.PI * projectedNormalVec.x;

    if (reverseX) {
        // rotX *= -1;
        rotY += Math.PI;
        // rotY *= -1;
        // rotY += Math.PI;
    }

    if (reverseY) {
        rotX += Math.PI;
        rotY *= -1;
    }

    const eu = new Euler(rotX, rotY, 0);
    const newRotMat = new Matrix4();
    newRotMat.makeRotationFromEuler(eu);
    // const worldRotMat = get(clipFrames)[get(appTime)].convertToLocalRotation(newRotMat);
    const worldRotMat = get(clipFrames)[get(appTime)].convertToWorldRotation(newRotMat);

    return worldRotMat;
}

function getZRot(rotMat) {
    const e = new Euler();
    e.setFromRotationMatrix(rotMat);
    return e.z;
}

export class CanvasGizmo {
    constructor(animatedCanvas) {
        this.animatedCanvas = animatedCanvas;
        this.selected = false;
    }

    get ID() {
        return "canvas" + this.animatedCanvas.ID;
    }

    select() {
        this.selected = true;
    }

    unselect() {
        this.selected = false;
    }

    drawTrajectory(time, interactable) {

        // Create svg polyline
        let svg = d3.select("svg#ui-overlay");

        // svg.selectAll("line#traj" + this.animatedCanvas.ID).remove();
        let trajectoryGroupID = "trajectory-" + this.ID;
        let trajectoryGroup = svg.select("#" + trajectoryGroupID);

        if (trajectoryGroup.empty()) {
            trajectoryGroup = svg.append("g")
                .attr("id", trajectoryGroupID);
        }

        trajectoryGroup.selectAll("line").remove();

        if (!interactable || !this.selected || this.animatedCanvas.type === "static" || this.animatedCanvas.hasDirtySegments || !this.animatedCanvas.trajectoryUpToDate)
          return;

        var gradientColor = (p) => {
            return d3.interpolateHslLong("red", "blue")((p.time)/get(clipFrames).length);
          };

        const projFrame = get(clipFrames)[time];
        let points = [];

        get(clipFrames).forEach((frame) => {
            let screenSpacePos = this.animatedCanvas.getProjectedPosition(frame.time, projFrame, false);
            screenSpacePos.time = frame.time;
            let depth = this.animatedCanvas.getProjectedDepth(frame.time, projFrame);
            screenSpacePos.opacity = ((depth > -1) && (depth < 1)) ? 1 : 0;

            points.push(screenSpacePos);

        });


        trajectoryGroup.selectAll("line")
            .data(points)
            .enter()
            .filter( (d, i) => d.x <= 1 && d.x >= 0 && d.y <= 1 && d.y >= 0 )
            .append("line")
            .attr("x1", (d, i) => d.x * svg.attr("width"))
            .attr("y1", (d, i) => d.y * svg.attr("height"))
            .attr("x2", (d, i) => (d.time + 1 < points.length) ? points[d.time+1].x * svg.attr("width") : points[d.time].x * svg.attr("width"))
            .attr("y2", (d, i) => (d.time + 1 < points.length) ? points[d.time+1].y * svg.attr("height") : points[d.time].y * svg.attr("height"))
            .attr('stroke', d => gradientColor(d))
            .attr('stroke-opacity', d => d.opacity)
            .attr('stroke-width', "10")
            .attr('stroke-linecap', "round")
            .on("click", (e, d) => {
                appTime.update(() => d.time);
            });

    }


    draw(time, visible=true) {
        const frame = get(clipFrames)[time];

        let interactable = visible && this.animatedCanvas.trajectoryUpToDate;

        // if (!frame.loaded)
        //     return false;

        let screenSpacePos = this.animatedCanvas.getProjectedPosition(time, frame);
        let depth = this.animatedCanvas.getProjectedDepth(time, frame);

        let outOfScreen = screenSpacePos.x < 0 || screenSpacePos.y < 0 || screenSpacePos.x > 1 || screenSpacePos.y > 1;

        // if (depth < -1 || depth > 1)
        //     visible = false;

        let svg = d3.select("svg#ui-overlay");

        const positionGizmoID = "position-" + this.ID;
        let positionGizmoGroup = svg.select("#" + positionGizmoID);

        if (visible && positionGizmoGroup.empty()) {

            positionGizmoGroup = svg.append("svg")
                .attr("id", positionGizmoID)
                .attr("width", gizmoDim.x)
                .attr("height", gizmoDim.y);

            let crosshairGroup = positionGizmoGroup
                .append("g")
                .classed("crosshair", true)

            const crosshairDim = gizmoDim.x / 2;
            const crosshairThickness = 5;
            
            crosshairGroup
                .append("rect")
                    .attr("id", this.ID)
                    .attr("x", gizmoDim.x * 0.5 - crosshairDim * 0.5)
                    .attr("y", gizmoDim.y * 0.5 - crosshairThickness * 0.5)
                    .attr("width", crosshairDim)
                    .attr("height", crosshairThickness)
            crosshairGroup
                .append("rect")
                    .attr("id", this.ID)
                    .attr("x", gizmoDim.x * 0.5 - crosshairThickness * 0.5)
                    .attr("y", gizmoDim.y * 0.5 - crosshairDim * 0.5)
                    .attr("width", crosshairThickness)
                    .attr("height", crosshairDim)
                    

            positionGizmoGroup
                .append("rect")
                .attr("id", this.ID)
                .attr("width", gizmoDim.x)
                .attr("height", gizmoDim.y)
                .attr("fill-opacity", 0);

            let arrowSVG = svg
                .append("svg")
                .attr("id", `arrow-${this.ID}`)
                .classed("arrow", true)
                .attr("width", hintArrowDim)
                .attr("height", hintArrowDim)
                .attr("overflow", "visible");

            let arrowGroup = arrowSVG.append("g")
            .attr("transform-origin", "center");


            arrowGroup
                .append("line")
                    .attr("x1", hintArrowDim * 0.1)
                    .attr("y1", hintArrowDim * 0.1)
                    .attr("x2", hintArrowDim * 0.5)
                    .attr("y2", hintArrowDim * 0.9)

            arrowGroup
                .append("line")
                    .attr("x1", hintArrowDim * 0.9)
                    .attr("y1", hintArrowDim * 0.1)
                    .attr("x2", hintArrowDim * 0.5)
                    .attr("y2", hintArrowDim * 0.9)

            let dragDeltaX = 0;
            let dragDeltaY = 0;

            const self = this;

            let dragHandler = d3.drag()
                .on("start", function(e) {
                    let current = d3.select(this);
                    if (!current.classed("draggable"))
                        return;
                    
                    dragDeltaX = current.attr("x") - e.x; 
                    dragDeltaY = current.attr("y") - e.y; 
                })
                .on("drag", function (e) {
                    if (!d3.select(this).classed("draggable"))
                        return;
                    d3.select(this)
                        .attr("x", e.x + dragDeltaX)
                        .attr("y", e.y + dragDeltaY);
                    
                    const kfProps = {x: self.getPosition().x, y: self.getPosition().y};
                    self.animatedCanvas.addKeyframe(get(appTime), kfProps);
                    animationController.updateCanvases();

                    
                })
                .on("end", (e) => {
                    // if (!d3.select(this).classed("draggable"))
                    //     return;
                    // d3.select(this)
                    //     .attr("x", e.x + dragDeltaX)
                    //     .attr("y", e.y + dragDeltaY);
                    
                    // const kfProps = {x: self.getPosition().x, y: self.getPosition().y};

                    if (self.animatedCanvas.type === "static")
                        self.animatedCanvas.inferTrajectory();

                    sessionLog.log(LogActionType.KeyframeAdd, {
                        canvasID: self.animatedCanvas.ID,
                        keyframeTime: get(appTime),
                        editedProps: ["x", "y"],
                        type: "gizmo",
                    }, false);
                });
            
            dragHandler(positionGizmoGroup);

            positionGizmoGroup.on("click", () => {
                animationController.selectCanvas(this.animatedCanvas.ID);
            })
        }

        positionGizmoGroup
            .attr("x", screenSpacePos.x * svg.attr("width") - gizmoDim.x * 0.5)
            .attr("y", screenSpacePos.y * svg.attr("height") - gizmoDim.y * 0.5)
            .attr("visibility", visible ? "visible" : "hidden")
            .classed("draggable", this.selected && interactable && visible)
            .classed("loading", !interactable)
            .classed("has-keyframe", this.animatedCanvas.isKeyframed(time, "x") || this.animatedCanvas.isKeyframed(time, "y") || this.animatedCanvas.isKeyframed(time, "depth"))


        let svgPos = new Vector2(screenSpacePos.x * svg.attr("width") - hintArrowDim * 0.5, screenSpacePos.y * svg.attr("height") - hintArrowDim * 0.5)
        let extremePos = svgPos.clone().clamp(new Vector2(10, 10), new Vector2(svg.attr("width") - hintArrowDim - 10, svg.attr("height") - hintArrowDim - 10));

        let dirVec = new Vector2();
        let angleToX = dirVec.subVectors(svgPos, extremePos).angle();
        let arrowSVG = svg.select(`svg#arrow-${this.ID}`)
            .attr("x", extremePos.x)
            .attr("y", extremePos.y)
            .attr("visibility", (outOfScreen && this.selected) ? "visible" : "hidden")


        arrowSVG.select("g")
            .attr("style", `transform: rotate(${-90 + angleToX * 180 / Math.PI}deg)`);

        return true;
    }

    drawOrientation(time, visible=true) {

        let interactable = visible && this.animatedCanvas.trajectoryUpToDate;

        const frame = get(clipFrames)[time];
        let svg = d3.select("svg#ui-overlay");

        const vecScreenLength = 40;

        const orientationGizmoID = "orientation-" + this.ID;

        let originPos = this.animatedCanvas.getProjectedPosition(time);
        let depth = this.animatedCanvas.getProjectedDepth(time, frame);

        if (depth < -1 || depth > 1)
            visible = false;

        if (!visible) {
            // Don't draw orientation gizmo, delete potential previous gizmo
            svg.select("#" + orientationGizmoID).remove();
            return;
        }

        // Project the normal vector of the plane
        // extremity = origin + projected normal vector
        let projectedNormal = this.animatedCanvas.getNormal(time, true);
        
        // Make proportions square
        projectedNormal.setX(projectedNormal.x * svg.attr("width") / svg.attr("height"));

        // Scale it to desired pixel size
        projectedNormal.multiplyScalar(0.5 * vecScreenLength);

        let extremityPos = originPos.clone();
        extremityPos.add(projectedNormal);

        let orientationGizmoGroup = svg.select("#" + orientationGizmoID);

        if (visible && orientationGizmoGroup.empty()) {

            orientationGizmoGroup = svg.append("g")
                .attr("id", orientationGizmoID);

            orientationGizmoGroup.on("click", () => {
                animationController.selectCanvas(this.animatedCanvas.ID);
            })

            const orientationGauge = orientationGizmoGroup
                .append("ellipse")
                    .attr("fill", "grey")
                    .style("transform-origin", "center")
                    .attr("opacity", 0.5);

            const orientationLine = orientationGizmoGroup
                .append("line")
                    .attr('stroke', "white")
                    .attr('stroke-width', "4")
                    .attr('stroke-linecap', "round");

            const orientationHandle = orientationGizmoGroup
                .append("circle")
                .attr("r", 10)
                .classed("gauge", true);
                    // .classed("has-keyframe", this.animatedCanvas.keyframes.hasOwnProperty(time));

            let dragDeltaX = 0;
            let dragDeltaY = 0;

            let reverseX, reverseY;
            let originalZRot;

            const self = this;

            let dragHandler = d3.drag()
                .on("start", function(e) {
                    let current = d3.select(this);

                    if (!current.classed("draggable"))
                        return;

                    dragDeltaX = current.attr("cx") - e.x; 
                    dragDeltaY = current.attr("cy") - e.y;

                    // Find out if the canvas starts out reversed
                    let r = self.animatedCanvas.getProjectedOrientation(get(appTime));
                    reverseX = r.reverseX;
                    reverseY = r.reverseY;

                    originalZRot = getZRot(self.animatedCanvas.getRotation(get(appTime)));

                })
                .on("drag", function (e) {
                    if (!d3.select(this).classed("draggable"))
                        return;

                    // New position
                    let dragX = e.x + dragDeltaX;
                    let dragY = e.y + dragDeltaY;

                    // New projected normal vector (clamp 2D vector norm)
                    let originPosX = orientationGizmoGroup.select("line").attr("x1");
                    let originPosY = orientationGizmoGroup.select("line").attr("y1");
                    const newProjectedNormal = new Vector2(dragX - originPosX, dragY - originPosY);
                    // newProjectedNormal.clampLength(0, vecScreenLength);

                    // console.log("projected normal screen length: " + newProjectedNormal.length());

                    const normalizedNewProjectedNormal = newProjectedNormal.clone();
                    normalizedNewProjectedNormal.divideScalar(vecScreenLength);

                    console.log(`reverseX = ${reverseX}, reverseY = ${reverseY}`);

                    let newRotMat = projectedNormalToRotation(normalizedNewProjectedNormal, originalZRot, reverseX, reverseY);
                    
                    // d3.select(this)
                    //     .attr("cx", originPos.x * svg.attr("width") + newProjectedNormal.x)
                    //     .attr("cy", originPos.y * svg.attr("height") + newProjectedNormal.y);

                    self.animatedCanvas.addKeyframe(get(appTime), {rot: newRotMat });
                    animationController.updateCanvases();


                    orientationLine
                        .attr("x2", originPos.x * svg.attr("width") + newProjectedNormal.x)
                        .attr("y2",  originPos.y * svg.attr("height") + newProjectedNormal.y)
                })
                .on("end", () => {

                    if (self.animatedCanvas.type === "static")
                        self.animatedCanvas.inferTrajectory();

                    sessionLog.log(LogActionType.KeyframeAdd, {
                        canvasID: self.animatedCanvas.ID,
                        keyframeTime: get(appTime),
                        editedProps: ["rot"],
                        type: "gizmo",
                    }, false); // Can have duplicates

                });
            
            dragHandler(orientationHandle);

            // canvasEl.on("click", () => {
            //     animationController.selectCanvas(this.animatedCanvas.ID);
            // })
        }
        // else {


        orientationGizmoGroup.style("visibility", visible ? "inherit" : "hidden");

        orientationGizmoGroup
            .select("line")
                .attr("x1", originPos.x * svg.attr("width"))
                .attr("y1", originPos.y * svg.attr("height"))
                .attr("x2", originPos.x * svg.attr("width") + projectedNormal.x)
                .attr("y2", originPos.y * svg.attr("height") + projectedNormal.y)

        orientationGizmoGroup
            .select("circle")
                .attr("cx",  originPos.x * svg.attr("width") + projectedNormal.x)
                .attr("cy", originPos.y * svg.attr("height") + projectedNormal.y)
                .classed("draggable", this.selected && visible && interactable)
                .classed("loading", !interactable)
                .classed("has-keyframe", this.animatedCanvas.isKeyframed(time, "rot"));

        let estimatedRX = 0.5 * vecScreenLength * Math.cos(0.5 * Math.PI * projectedNormal.x / vecScreenLength);
        let estimatedRY = 0.5 * vecScreenLength * Math.cos(0.5 * Math.PI * projectedNormal.y / vecScreenLength);
        orientationGizmoGroup
            .select("ellipse")
                .attr("cx",  originPos.x * svg.attr("width"))
                .attr("cy", originPos.y * svg.attr("height"))
                .attr("rx", estimatedRX > 0.1 ? estimatedRX : 0)
                .attr("ry", estimatedRY > 0.1 ? estimatedRY : 0)
                // .style("transform", `skewX(${-0.1 * Math.PI * projectedNormal.x / vecScreenLength}rad)`);

            // console.log("skewX " + 0.5 * Math.PI * projectedNormal.x / vecScreenLength);

        // }
    }

    getPosition() {
        let svg = d3.select("svg#ui-overlay");
        let x = (+d3.select("#position-" + this.ID).attr("x") + 0.5 * gizmoDim.x) / svg.attr("width");
        let y = (+d3.select("#position-" + this.ID).attr("y") + 0.5 * gizmoDim.y) / svg.attr("height");

        return new Vector2(x, y);
    }

    delete() {
        let svg = d3.select("svg#ui-overlay");
        svg.select("#position-" + this.ID).remove();
        svg.select(`svg#arrow-${this.ID}`).remove();
        svg.selectAll("#trajectory-" + this.ID).remove();
        svg.select("#orientation-" + this.ID).remove();
    }
}
