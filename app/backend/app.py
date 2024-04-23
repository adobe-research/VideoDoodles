#!/usr/bin/env python

import asyncio
import json
import os
import ssl
import time
from datetime import datetime
from typing import List, Tuple

import numpy as np
import websockets

from scripts.convert import (get_default_position_at, get_update_free_zones,
                             jsonize, parse_trajectory_data)
from scripts.paths import get_available_videos
from scripts.solve_trajectory import find_orientations, find_positions
from scripts.state_management import unique_ID, update_canvas_state
from scripts.utils import orientation_slerp


try:
    width = os.get_terminal_size().columns 
except:
    width = 20

async def send_canvas_message(
        websocket,
        canvas_id    : int,
        status       : str,
        message      : str,
        frame_indices: List,
        positions    : List = None,
        orientations : List = None,  ): 

    json_message = {
                "status": status,
                "message": message,
                "canvasID": canvas_id,
                "frameIndices": frame_indices
            }
    if positions is not None:
        json_message['positions'] = positions

    if orientations is not None:
        json_message['orientations'] = orientations

    print(f"Sending result for canvas {canvas_id} to websocket server. Status = {status}.")

    await websocket.send(
        json.dumps(
            json_message
        ))


async def handle_exception(websocket, error_message, status="ERROR"):
    print("Error:", error_message)
    message = {
                "status": status,
                "message": error_message
            }
    
    await websocket.send(
        json.dumps(
            message
        ))

async def handler(websocket):

    state_per_canvas = {}

    while True:
        try:
            message = await websocket.recv()
        except websockets.exceptions.ConnectionClosedOK:
            print("Closed connection.")
            break
        except websockets.exceptions.ConnectionClosedError:
            print("Closed connection.")
            break
        # async for message in websocket:
        print("=" * width)
        print("Received websocket message.")
        data = json.loads(message)

        try:
            action = data["action"]
        except Exception as e:
            await handle_exception(websocket, "Malformed input message. " + str(e))
            continue

        print(f"Requested action = {action}")

        if action == "GET_VIDEO_LIST":
            # Return the list of videos available in the server
            vids = get_available_videos()
            # print(vids)
            await websocket.send(
                json.dumps(
                    {
                        "status": "VIDEO_LIST",
                        "message": "Get the list of videos available in backend.",
                        "videosList": vids
                    }
                ))
        elif action == "INIT_STATE":
            state_per_canvas.clear()
            print("Reset backend canvas state log.")

        elif action == "EXPORT_KEYFRAMES":
            print("Saving keyframes from UI...")
            try:
                canvas_id = data["canvasID"]
            except Exception as e:
                await handle_exception(websocket, "Malformed input message. " + str(e), "ESTIMATION_FAILURE")
                continue

            try:
                mvt_type, clip, clip_length, camera_data, position_kfs, orientation_kfs, position_segments, orientation_segments  = parse_trajectory_data(data)
            except Exception as e:
                await handle_exception(websocket, "Malformed input message. " + str(e), "ESTIMATION_FAILURE")
                continue

            if not os.path.exists('keyframe_records'):
                os.makedirs('keyframe_records')

            file_name = f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_{clip}_{canvas_id}.json"
            
            with open(os.path.join('keyframe_records', file_name), 'w') as f:
                json.dump({'clip': clip, 'mvt_type': mvt_type, 'position_keyframes': jsonize(position_kfs), 'orientation_keyframes': jsonize(orientation_kfs)}, f)

            print(f"Saved keyframes at keyframe_records/{file_name}")

        elif action == "INFER_TRAJECTORY":
            try:
                canvas_id = data["canvasID"]
            except Exception as e:
                await handle_exception(websocket, "Malformed input message. " + str(e), "ESTIMATION_FAILURE")
                continue

            try:
                mvt_type, clip, clip_length, camera_data, position_kfs, orientation_kfs, position_segments, orientation_segments  = parse_trajectory_data(data)
            except Exception as e:
                await handle_exception(websocket, "Malformed input message. " + str(e), "ESTIMATION_FAILURE")
                continue

            # Initialize state
            update_canvas_state(state_per_canvas, clip, canvas_id, clip_length)
            # try:
            if mvt_type == "static":
                res = camera_data["res"]

                pos_keyframes = [kf for kf in position_kfs if ("pos_3d" in kf.keys()) or ("pos_2d" in kf.keys())]

                if len(pos_keyframes) >= 1:
                    print(f"Using only first keyframe of {len(pos_keyframes)} given keyframes.")
                    kf = pos_keyframes[0]
                    pt_3d = get_default_position_at(kf, clip) / camera_data["down_scale_factor"]
                    trajectory = np.tile(pt_3d, clip_length).reshape((-1,3))

                    await send_canvas_message(
                        websocket, 
                        canvas_id, 
                        status = "ESTIMATION_POSITION_SUCCESS", 
                        message = f"Found a static position for canvas {canvas_id}.",
                        frame_indices = np.arange(clip_length).tolist(),
                        positions = trajectory.tolist())

                else:
                    await send_canvas_message(
                            websocket, 
                            canvas_id, 
                            status = "ESTIMATION_POSITION_UNCHANGED", 
                            message = f"Please add at least 1 position keyrame for canvas {canvas_id}.",
                            frame_indices = np.arange(clip_length).tolist())


                orientation_trajectory = orientation_slerp(orientation_kfs, start_frame=0, end_frame=clip_length-1)

                await send_canvas_message(
                        websocket, 
                        canvas_id, 
                        status = "ESTIMATION_ORIENTATION_SUCCESS", 
                        message = f"Found a static orientation for canvas {canvas_id}.",
                        frame_indices = np.arange(clip_length).tolist(),
                        orientations = orientation_trajectory.reshape((clip_length, -1)).tolist())

            elif mvt_type == "dynamic":

                # Determine which index ranges need an update...
                frames_that_dont_need_update_pos = get_update_free_zones(position_segments, clip_length)
                frames_that_dont_need_update_rot = get_update_free_zones(orientation_segments, clip_length)

                if len(frames_that_dont_need_update_pos) > 0:
                    # Send message about non updated frames
                    await send_canvas_message(
                        websocket, 
                        canvas_id, 
                        status = "ESTIMATION_POSITION_UNCHANGED", 
                        message = "",
                        frame_indices = frames_that_dont_need_update_pos.tolist())

                if len(frames_that_dont_need_update_rot) > 0:
                    # Send message about non updated frames
                    await send_canvas_message(
                        websocket, 
                        canvas_id, 
                        status = "ESTIMATION_ORIENTATION_UNCHANGED", 
                        message = "",
                        frame_indices = frames_that_dont_need_update_rot.tolist())

                trajectory, velocities, matching_weights = find_positions(
                    clip, 
                    camera_data, 
                    position_kfs, 
                    position_segments,
                    state_per_canvas[unique_ID(clip, canvas_id)]    
                )

                await send_canvas_message(
                        websocket, 
                        canvas_id, 
                        status = "ESTIMATION_POSITION_SUCCESS", 
                        message = f"Found a 3D trajectory for canvas {canvas_id}.",
                        frame_indices = np.arange(len(trajectory)).tolist(),
                        positions = trajectory.tolist())

                update_canvas_state(state_per_canvas, clip, canvas_id, clip_length, positions=trajectory * camera_data["down_scale_factor"], velocities=velocities, orientation_matching_weights=matching_weights, indices=np.arange(len(trajectory)))

                orientations_per_range = find_orientations(
                    orientation_kfs, 
                    velocities, 
                    matching_weights,
                    orientation_segments
                )

                for (orientations, segment) in zip(orientations_per_range, orientation_segments):
                    idx_range = np.arange(segment["start"], segment["end"] + 1)


                    if len(idx_range) > 0 and segment["dirty"]:
                        # print(idx_range, orientations.shape, segment["dirty"])

                        await send_canvas_message(
                            websocket, 
                            canvas_id, 
                            status = "ESTIMATION_ORIENTATION_SUCCESS", 
                            message = f"Found orientations for canvas {canvas_id}, segment [{segment['start']}, {segment['end']}].",
                            frame_indices = idx_range.tolist(),
                            orientations = orientations.reshape((len(idx_range), -1)).tolist())

                        update_canvas_state(state_per_canvas, clip, canvas_id, clip_length, orientations=orientations)
                        

            else :
                print("Error: Unrecognized movement type")

            # except Exception as e:
            #     await handle_exception(websocket, "Couldn't solve for trajectory or orientations. " + str(e), "ESTIMATION_FAILURE")
            #     continue


        else:
            print("unrecognized action", data["action"])



async def main():
    print("Starting backend server. Waiting for websocket messages... (Press Ctrl + C to quit)")
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())