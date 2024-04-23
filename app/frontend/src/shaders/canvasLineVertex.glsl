uniform vec3 canvasPos;
uniform mat4 canvasRot;
uniform float canvasScale;

uniform float lineWidth;

attribute vec2 instanceStart;
attribute vec2 instanceEnd;

// attribute float depthOffset;

// attribute vec2 uv;

varying vec2 vUv;

void main() {
    
    vec4 mvStart = modelViewMatrix * (vec4( canvasPos, 1.0 ) + canvasRot * vec4( instanceStart.x * canvasScale, instanceStart.y * canvasScale, 0.0, 0.0));
    vec4 mvEnd = modelViewMatrix * (vec4( canvasPos, 1.0 ) + canvasRot * vec4( instanceEnd.x * canvasScale, instanceEnd.y * canvasScale, 0.0, 0.0));

    vec4 screenSpaceStart = projectionMatrix * mvStart;
    vec4 screenSpaceEnd = projectionMatrix * mvEnd;

    float aspect = projectionMatrix[1][1] / projectionMatrix[0][0];

    // clip space
    vec3 ndcStart = screenSpaceStart.xyz; // / screenSpaceStart.w;
    vec3 ndcEnd = screenSpaceEnd.xyz;// / screenSpaceEnd.w;
    // direction
    vec2 dir = ndcEnd.xy - ndcStart.xy;
    // account for clip-space aspect ratio
    dir.x *= aspect;
    dir = normalize( dir );

    vec2 offset = vec2( dir.y, - dir.x );
    // undo aspect ratio adjustment
    dir.x /= aspect;
    offset.x /= aspect;
    // sign flip
    if ( position.x < 0.0 ) offset *= - 1.0;
    // endcaps
    if ( position.y < 0.0 ) {
        offset += - dir;
    } else if ( position.y > 1.0 ) {
        offset += dir;
    }
    // adjust for linewidth
    offset *= lineWidth;
    // adjust for clip-space to screen-space conversion // maybe resolution should be based on viewport ...
    // offset /= resolution.y;
    // select end
    vec4 clip = ( position.y < 0.5 ) ? screenSpaceStart : screenSpaceEnd;
    // back to clip space
    // offset *= clip.w;
    clip.xy += offset;

    gl_Position = clip;


    vUv = uv;

}