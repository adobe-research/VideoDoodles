
function shallowEqual(object1, object2) {
    const keys1 = Object.keys(object1);
    const keys2 = Object.keys(object2);
    if (keys1.length !== keys2.length) {
      return false;
    }
    for (let key of keys1) {
      if (object1[key] !== object2[key]) {
        return false;
      }
    }
    return true;
  }

class SessionLog {
    constructor() {
        this.actions = [];
    }

    startSession() {
        this.startTime = Date.now();
        this.actions = []; // clear any previous actions
    }

    log(action, props, noDuplicates=true) {
        const newEntry = {
            action: action,
            props: props,
            time: Date.now()
        }
        // Try to squash entry
        if (noDuplicates && this.actions.length > 0) {
            // Check previous entry, if it's identical, ignore
            let prevEntry = this.actions[this.actions.length - 1];
            if (prevEntry.action === action && shallowEqual(prevEntry.props, newEntry.props)) {
                // console.log("avoid logging duplicate action")
                return;
            }
        }

        this.actions.push(newEntry);
    }

    export() {
        return {
            startTime: this.startTime,
            endTime: Date.now(),
            actions: this.actions
        }
    }

    hasStarted() {
        return Date.now() > this.startTime;
    }

}

export const sessionLog = new SessionLog();

export const LogActionType = {
    ModeSwitch: "mode_switch",
    NavigateTime: "navigate_time",
    CanvasCreate: "canvas_create",
    CanvasDelete: "canvas_delete",
    CanvasSetType: "canvas_set_type",
    CanvasSetScale: "canvas_set_scale",
    KeyframeAdd: "keyframe_add",
    KeyframeRemove: "keyframe_remove",
    StrokeCreate: "stroke_create",
    StrokeDelete: "stroke_delete",
    TrajectoryInfer: "trajectory_infer",
    TrajectorySolved: "trajectory_solved",
    FrameCreate: "frame_create",
    FrameDelete: "frame_delete"
}