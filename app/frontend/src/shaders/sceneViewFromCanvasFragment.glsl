uniform vec2 resolution;
uniform vec2 viewportResolution;
uniform sampler2D viewportImage;

uniform mat4 VP;
uniform mat4 rot;
uniform vec3 pos;
uniform float scale;

// uniform float opacity;

void main( void ) {
    // gl_FragCoord is a screen space coordinate (0, 0) to (width, height)
    vec2 position = gl_FragCoord.xy / resolution;
    position = position * 2.0 - 1.0;

    vec4 projectedPos = VP * vec4(pos, 1.0) + VP * rot * vec4(scale * position.x, scale * position.y, 0.0, 0.0);
    vec2 viewportPosition = projectedPos.xy / projectedPos.w;
    // viewportPosition /= viewportResolution;
    viewportPosition = (viewportPosition + 1.0) * 0.5;
    // If out of frame, ignore
    if (viewportPosition.x > 1.0 || viewportPosition.y > 1.0 || viewportPosition.x < 0.0 || viewportPosition.y < 0.0) {
        discard;
    }
    // vec4 col = texture2D(viewportImage, viewportPosition.xy);
    vec4 col = texture2D(viewportImage, viewportPosition);
    gl_FragColor = col;
    gl_FragColor.a = 1.0;

    // gl_FragColor = vec4(viewportPosition.x, viewportPosition.y, 0.0, 1.0);

}