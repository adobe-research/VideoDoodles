import { Vector3, Vector2, Matrix4, Vector4, Euler } from 'three';
import { derived, get, writable } from 'svelte/store';



import { AnimatedCanvas } from './AnimatedCanvas.js';

import { clipFrames, clipName, time as appTime } from './store.js';
import Canvas from './Canvas.js';
import { send } from './websocket.js';

import { LogActionType, sessionLog } from "./SessionLog.js";

class TrajectoryPoint {
    constructor(position, rotation) {
        this.position = position;
        this.rotation = rotation;
        this.positionSolved = false;
        this.rotationSolved = false;
    }

    get solved() {
        return this.positionSolved && this.rotationSolved;
    }

    export() {
        return {
            'position': this.position,
            'rotation': this.rotation
        }
    }
}

export let saveToLoad = {
    data: undefined,
};


class AnimationController {
    constructor() {
        // this._animatedCanvases = writable([]);
        this._animatedCanvases = writable({});
        // this.selectedCanvasID = -1;
        this._selectedCanvasID = writable(-1);
        this.newCanvasUniqueID = 0;
        this.selectedCanvas = derived(
            [this._animatedCanvases, this._selectedCanvasID], 
            ([$canvases, $id]) => {
                if ($id === -1)
                    return undefined;
                if ($id in $canvases)
                    return $canvases[$id];
                return undefined;
            })
    }

    get animatedCanvases() {
        return this._animatedCanvases;
    }

    get selectedCanvasID() {
        return get(this._selectedCanvasID);
    }

    reset() {
        this.newCanvasUniqueID = 0;
        // Delete all canvas objects
        Object.values(get(this._animatedCanvases)).forEach(c => {
            c.delete();
        });

        this._animatedCanvases.update(() => ({}));
        this._selectedCanvasID.update(() => -1);

        // Notify server that the scene has been reset
        send(
            { "action": "INIT_STATE" }
        )
    }

    addCanvas() {
        const canvas = new Canvas();
        const defaultPos = get(clipFrames)[get(appTime)].screenSpaceToWorldSpace(0.5, 0.5);

        // Generate a default trajectory
        let defaultTraj = [];
        for (let i = 0; i < get(clipFrames).length; i++) {
            defaultTraj.push(new TrajectoryPoint(defaultPos.clone(), new Matrix4()));
        }
        // Set canvas ID
        canvas.ID = this.newCanvasUniqueID;

        this.newCanvasUniqueID++;

        // Store animated canvas
        const ac = new AnimatedCanvas(canvas, defaultTraj);
        ac.addKeyframe(get(appTime), {"x": 0.5, "y": 0.5})
        // ac.setTime(get(appTime));

        sessionLog.log(LogActionType.CanvasCreate, {canvasID: ac.ID});

        this._animatedCanvases.update((animatedCanvases) => { animatedCanvases[canvas.ID] = ac; return animatedCanvases; });

        this.selectCanvas(ac.ID);
    }

    deleteSelectedCanvas() {
        if (this.selectedCanvasID !== -1) {
            this.deleteCanvas(this.selectedCanvasID);
        }
    }

    deleteCanvas(canvasID) {
        this._animatedCanvases.update((animatedCanvases) => {
            if (canvasID in animatedCanvases) {
                animatedCanvases[canvasID].delete();
                sessionLog.log(LogActionType.CanvasDelete, {canvasID: canvasID});
                delete animatedCanvases[canvasID];
            }
            return animatedCanvases;
        });

        this._selectedCanvasID.update((id) => (id == canvasID) ? -1 : id );
    }

    update() {
        this.updateAnimations();
    }

    updateAnimations() {
        const time = get(appTime);
        this._animatedCanvases.update((animatedCanvases) => {
            Object.values(animatedCanvases).forEach((canvas) => {
                canvas.setTime(time);
            });
            return animatedCanvases;
        });
    }

    drawGizmos(uiMode, editTool="move") {
        const time = get(appTime);
        Object.values(get(this._animatedCanvases)).forEach((c) => {
            // console.log(c.ID);
            // if (get(this._selectedCanvasID) === c.ID) {
            c.gizmo.drawTrajectory(time, uiMode == "edit");
            // }
            c.gizmo.draw(time, uiMode == "edit" && editTool == "move");
            c.gizmo.drawOrientation(time, uiMode == "edit" && editTool == "rotate");
        })
    }

    // setDrawing(drawingCanvas) {
    //     if (get(this._selectedCanvasID) !== -1) {

    //         this._animatedCanvases.update((animatedCanvases) => {

    //             const c = animatedCanvases[get(this._selectedCanvasID)];
    //             c.canvas.setTexture(drawingCanvas);

    //             return animatedCanvases;
    //         });
    //     }
    // }

    // getDrawing() {
    //     let selectedCanvasDrawing = undefined;
    //     if (get(this._selectedCanvasID) !== -1) {
    //         selectedCanvasDrawing = get(this._animatedCanvases)[get(this._selectedCanvasID)].canvas.getTexture();
    //     }
    //     return selectedCanvasDrawing;
    // }

    toggleType() {
        if (get(this._selectedCanvasID) !== -1) {
            this._animatedCanvases.update((animatedCanvases) => {
                const c = animatedCanvases[get(this._selectedCanvasID)];

                if (c.type === "static")
                    c.setType("dynamic");
                else
                    c.setType("static");

                return animatedCanvases;
            })
        }
    }

    translate(vec) {
        if (get(this._selectedCanvasID) !== -1) {
            this._animatedCanvases.update((animatedCanvases) => {
                const c = animatedCanvases[get(this._selectedCanvasID)];
                // modify all positions of trajectory by translating them
                for (let i = 0; i < get(clipFrames).length; i++) {
                    c.trajectory[i].position.add(vec);
                }

                return animatedCanvases;
            });
            this.updateAnimations();
        }
    }

    // setPositions(canvasID, positions) {
    //     this._animatedCanvases.update((animatedCanvases) => {
    //         if (canvasID in animatedCanvases) {
    //             animatedCanvases[canvasID].applyInferredTrajectory(positions)
    //         }
    //         return animatedCanvases;
    //     });

    //     this.updateAnimations();
    // }

    // setRotations(canvasID, rotations) {
    //     this._animatedCanvases.update((animatedCanvases) => {
    //         if (canvasID in animatedCanvases) {
    //             animatedCanvases[canvasID].trajectory.forEach((trajectoryPt, idx) => {
    //                 trajectoryPt.rotation = rotations[idx];
    //             })
    //         }
    //         return animatedCanvases;
    //     });
    //     console.log(get(this._animatedCanvases))
    //     this.updateAnimations();
    // }

    setTrajectory(canvasID, positions, rotations, indices) {
        // console.log("set trajectory")

        this._animatedCanvases.update((animatedCanvases) => {
            if (canvasID in animatedCanvases) {
                animatedCanvases[canvasID].applyInferredTrajectory(positions, rotations, indices);
            }
            return animatedCanvases;
        });
        console.log(get(this._animatedCanvases))
        this.updateAnimations();
    }

    markTrajectoryPoints(canvasID, indices, positionSolved, orientationSolved) {
        this._animatedCanvases.update((animatedCanvases) => {
            if (canvasID in animatedCanvases) {
                animatedCanvases[canvasID].markTrajectoryPoints(positionSolved, orientationSolved, indices);
            }
            return animatedCanvases;
        });
        this.updateAnimations();
    }

    abortedEstimation(canvasID) {
        this._animatedCanvases.update((animatedCanvases) => {
            if (canvasID in animatedCanvases) {
                animatedCanvases[canvasID].trajectoryUpToDate = true;

                // Mark all segments as clean
                Object.values(animatedCanvases[canvasID].positionSegments).forEach((s) => {
                    s.markClean();
                })

                Object.values(animatedCanvases[canvasID].orientationSegments).forEach((s) => {
                    s.markClean();
                })
            }
            return animatedCanvases;
        });

        
    }

    debugSetPosition(canvasID, pos) {
        console.log("set position")
        let traj = [];
        for (let i = 0; i < get(clipFrames).length; i++) {
            traj.push(pos);
        }
        this.setPositions(canvasID, traj);
    }

    debugSetRotation(canvasID, rot) {
        let traj = [];
        for (let i = 0; i < get(clipFrames).length; i++) {
            traj.push(rot);
        }
        this.setRotations(canvasID, traj);
    }

    debugAddKeyframe(canvasID, time, props) {
        this._animatedCanvases.update((animatedCanvases) => {
            if (canvasID in animatedCanvases) {
                animatedCanvases[canvasID].addKeyframe(time, props);
                animatedCanvases[canvasID].inferTrajectory();
            }

            return animatedCanvases;
        });
    }


    selectCanvas(canvasID) {
        if (canvasID < 0 || canvasID >= get(this.animatedCanvases).length)
            return false;

        console.log("selecting canvas " + canvasID);


        // Mark all as unselected, except the one
        this.unselectAll();
        this._animatedCanvases.update((animatedCanvases) => {
            animatedCanvases[canvasID].select();
            return animatedCanvases;
        });

        this._selectedCanvasID.update((prev) => canvasID);

        return true;
    }

    unselectAll() {
        // this.selectedCanvasID = -1;
        this._selectedCanvasID.update((prev) => -1);

        this._animatedCanvases.update((animatedCanvases) => {
            Object.values(animatedCanvases).forEach((c) => c.unselect());
            return animatedCanvases;
        });
    }

    updateCanvases() {
        // Trigger an update of the store
        this._animatedCanvases.update((canvases) => canvases);
    }

    exportCurrentCanvases() {

        let exportedCanvases = Object.values(get(this._animatedCanvases)).map(c => {
            return c.export();
        });

        console.log(exportedCanvases);
        return {
            canvases: exportedCanvases,
            clip: get(clipName),
        }
    }

    loadExportedScene(sceneData) {
        console.log("load exported scene");
        const canvasesData = sceneData.canvases;
        let maxCanvasID = -1;
        canvasesData.forEach((c) => {
            // Create a canvas with that data
            const canvas = new Canvas();
            // Set canvas ID
            canvas.ID = c.canvasID;
            maxCanvasID = Math.max(maxCanvasID, c.canvasID);

            // Load trajectory from data
            let defaultTraj = [];
            for (let i = 0; i < c.trajectory.length; i++) {
                let mat = new Matrix4();
                mat.copy(c.trajectory[i].rotation);
                let pos = c.trajectory[i].position;
                defaultTraj.push(new TrajectoryPoint(
                    new Vector3(pos.x, pos.y, pos.z),
                    mat
                ));
            }

            const ac = new AnimatedCanvas(canvas, defaultTraj);
            ac.type = c.type;
            ac.canvas.scale = c.scale;

            // Load keyframes
            ac.loadKeyframes(c.keyframes);

            // Load segments
            ac.loadSegments(c.positionSegments, c.orientationSegments);

            // Load animationClip (strokes)
            ac.loadAnimationClip(c.animationClip);


            // Store animated canvas
            this._animatedCanvases.update((animatedCanvases) => { animatedCanvases[canvas.ID] = ac; return animatedCanvases; });

        })


        this.newCanvasUniqueID = maxCanvasID + 1;
    }
    
}

export const animationController = new AnimationController();