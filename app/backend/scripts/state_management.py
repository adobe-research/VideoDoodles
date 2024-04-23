import numpy as np


def unique_ID(clip, canvasID):
    return f"{clip}_{canvasID}"

def update_canvas_state(state_per_canvas, clip, canvasID, clip_length, positions=None, orientations=None, velocities=None, orientation_matching_weights=None, indices=None):
    id = unique_ID(clip, canvasID)
    if id in state_per_canvas.keys():
        previous_state = state_per_canvas[id]
    else:
        # Initialize (must be the same as in the web app)
        previous_state = {
            "positions": np.tile(np.zeros(3), (clip_length, 1)),
            "orientations": np.tile(np.eye(3), (clip_length, 1, 1)),
            "velocities": np.tile(np.zeros(3), (clip_length, 1)),
            "orientation_matching_weights": np.zeros(clip_length)
        }
    new_state = {
        "positions": positions,
        "orientations": orientations,
        "velocities": velocities,
        "orientation_matching_weights": orientation_matching_weights
    }
    state = {}

    for k in new_state.keys():
        state[k] = previous_state[k]
        if new_state[k] is not None:
            if indices is not None:
                state[k][indices] = new_state[k]
            else:
                state[k] = new_state[k]

    state_per_canvas[id] = state
