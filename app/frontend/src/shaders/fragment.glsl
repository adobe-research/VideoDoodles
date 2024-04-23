
// precision mediump float;

// uniform vec2 resolution;
// uniform vec2 viewOffset;
uniform sampler2D tex;
uniform sampler2D depthTex;

uniform float opacity;

uniform float depthOffset;
uniform float depthRange;

uniform float farPlane;
uniform float nearPlane;

varying vec2 clipPos;


precision highp float;

float worldToClip(highp float depth) {
    return (1.0/depth - 1.0/nearPlane) / (1.0/farPlane - 1.0/nearPlane);
}

void main( void ) {
    vec2 position = 0.5 * (clipPos + vec2(1.0, 1.0));
    // If out of frame, ignore
    if (position.x > 1.0 || position.y > 1.0) {
        discard;
    }
    vec2 uvCol = vec2(position.x, position.y);
    vec4 col = texture2D(tex, uvCol);
    gl_FragColor = col;
    gl_FragColor.a = opacity;

    // gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);

    vec2 uvDepth = vec2(position.x, position.y);
    // Unpack 16 bits depth from 8-bits B and G channels
    float depth = texture2D(depthTex, uvDepth).b * (256.0 / 257.0);
    depth += texture2D(depthTex, uvDepth).g * (1.0 / 257.0);
    depth = depthRange * depth + depthOffset;
    gl_FragDepth = worldToClip(depth);
}