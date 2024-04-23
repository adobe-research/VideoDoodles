uniform vec3 pos;
uniform mat4 rot;
uniform float scale;

uniform bool worldSpace;

// attribute float depthOffset;

// attribute vec2 uv;

varying vec2 vUv;

void main() {
    vec4 mvPos;

    if (worldSpace) {
        // mvPos = modelViewMatrix * vec4( pos, 1.0 ); // world space canvas
        mvPos = modelViewMatrix * (vec4( pos, 1.0 ) + rot * vec4( position.x * scale, position.y * scale, 0.0, 0.0)); // world space canvas
    }
    else {
        mvPos = vec4( pos.x, pos.y, pos.z, 1.0 ); // screen space canvas
    }

    // mvPos += rot * vec4( position.x * scale.x, position.y * scale.y, 0.0, 0.0);
    vec4 screenSpacePos = projectionMatrix * mvPos;
    // vec4 screenSpacePos = projectionMatrix * mvPos + vec4( position.x * scale.x, position.y * scale.y, 0.0, 0.0);

    gl_Position = screenSpacePos;

    // vec4 mvPos = modelViewMatrix * vec4( position, 1.0 );
    // gl_Position = projectionMatrix * mvPos;

    vUv = uv;

    // gl_Position = vec4(position.x, position.y, 0.0, 1.0);
}