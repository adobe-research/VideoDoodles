// import { canvasTransformData } from './store.js';
import { animationController } from './AnimationController.js';
import { Vector3 } from 'three';

import { message as messageStore, criticalErrorMessage, availableClips } from './store.js';
import { Matrix3 } from 'three';
import { Matrix4 } from 'three';

const websocket = new WebSocket(getWebSocketServer());

const connectionPromise = new Promise((resolve, reject) => {
  websocket.onopen = () => {
    console.log("connected");
    resolve(websocket);
  };
  websocket.onerror = error => {
    reject(error); 
    console.error(error);
    criticalErrorMessage.set("Can't connect to websocket server.")
  }

  websocket.onclose = () => {
    console.error("Websocket connection closed!"); 
    criticalErrorMessage.set("Websocket connection was closed.");
  }
})

const parseTrajectory = ((trajectory) => {
  return trajectory.map(xyz => new Vector3(xyz[0], xyz[1], xyz[2]))
});

const parseOrientationTrajectory = ((trajectory) => {
  return trajectory.map(e => { 
    let m = new Matrix3(); 
    m.set(...e);
    let m4 = new Matrix4();
    m4.setFromMatrix3(m);
    return m4; });
})

function getWebSocketServer() {
  if (window.location.host.includes("devbox.training.adobesensei.io")) {
    console.log("Connecting to socket at: " + "wss://" + window.location.host + "/backend");
    return "wss://" + window.location.host + "/backend";
  } else if (window.location.host.includes("localhost")) {
    return "ws://localhost:8001/";
  } else if (window.location.host.includes("inria")) {
    console.log("Connecting to Inria socket at: " + "ws://" + window.location.host + "/websocket");
    return "wss://" + window.location.host + "/websocket";
  }
  else {
    throw new Error(`Unsupported host: ${window.location.host}`);
  }
}

const expectedKeysPerStatus = {
  'ERROR': [
    "message"
  ],
  'VIDEO_LIST': [
    "message",
    "videosList"
  ],
  'ESTIMATION_POSITION_SUCCESS': [
    "message",
    "canvasID",
    "positions",
    "frameIndices"
  ],
  'ESTIMATION_ORIENTATION_SUCCESS': [
    "message",
    "canvasID",
    "orientations",
    "frameIndices"],
  'ESTIMATION_FAILURE': [
    "message",
    "canvasID",
    "frameIndices"
  ],
  'ESTIMATION_POSITION_UNCHANGED': [
    "message",
    "canvasID",
    "frameIndices"
  ],
  'ESTIMATION_ORIENTATION_UNCHANGED': [
    "message",
    "canvasID",
    "frameIndices"
  ]
}


websocket.addEventListener("message", ({ data }) => {

  const d = JSON.parse(data);

  console.log("received ");
  console.log(d);

  let status;

  if ("status" in d) {
    status = d["status"];
  }
  else {
    console.error("Invalid response from websocket.");
    return;
  }

  expectedKeysPerStatus[status].forEach((k) => {
    if (!k in d) {
      console.error(`Invalid response from websocket. Missing property: ${k}.`);
      animationController.abortedEstimation(canvasID);
      return;
    }
  });

  let message = d["message"];
  messageStore.set("Server: "+ message);


  if (status == "ERROR") {
    console.error(`Websocket returned an error. Message: ${d["message"]}`);
    return;
  }

  if (status == "VIDEO_LIST") {
    console.log("list of videos:")
    console.log(d["videosList"])
    availableClips.set(d["videosList"]);
    return;
  }

  let canvasID = d["canvasID"];

  if (status == "ESTIMATION_POSITION_SUCCESS") {
    let positions = parseTrajectory(d["positions"]);

    animationController.setTrajectory(canvasID, positions, undefined, d["frameIndices"]);
  }

  if (status == "ESTIMATION_ORIENTATION_SUCCESS") {
    let orientations = parseOrientationTrajectory(d["orientations"]);

    animationController.setTrajectory(canvasID, undefined, orientations, d["frameIndices"]);
  }


  if (status == "ESTIMATION_POSITION_UNCHANGED") {
    animationController.markTrajectoryPoints(canvasID, d["frameIndices"], true, undefined);
  }
  if (status == "ESTIMATION_ORIENTATION_UNCHANGED") {
    animationController.markTrajectoryPoints(canvasID, d["frameIndices"], undefined, true);
  }
  if (status == "ESTIMATION_FAILURE")
    animationController.abortedEstimation(canvasID);

});

export const send = (message) => {
  connectionPromise
    .then(() => {
      console.log("sent message to websocket: " + JSON.stringify(message));
      websocket.send(JSON.stringify(message));
    })
    .catch(() => {
      console.error("Websocket couldn't connect, can't send message.")
    })

}