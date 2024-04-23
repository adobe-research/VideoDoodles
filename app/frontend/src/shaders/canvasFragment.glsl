
uniform sampler2D tex;
uniform float opacity;
uniform bool debug;
uniform float backgroundOpacity;
uniform vec3 backgroundColor;

varying vec2 vUv;

void main() {

    // vec2 position = (gl_FragCoord.xy + viewOffset) / resolution;
    // gl_FragColor = 0.5 * vec4( vUv.x, vUv.y, 0.0, 1.0 );
    vec4 col = texture2D(tex, vUv );
    gl_FragColor = col;
    gl_FragColor.a *= opacity;
    // gl_FragColor.a = 1.0;
    // gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);

    if (debug && (vUv.x < 0.01 || vUv.x > 0.99 || vUv.y < 0.01 || vUv.y > 0.99)) {
        gl_FragColor = vec4( vUv.x, vUv.y, 0.0, 1.0 );
    }


    // // Debug vis
    // gl_FragColor = vec4(backgroundColor, 0.8);
    // if ((vUv.x < 0.03 || vUv.x > 0.97 || vUv.y < 0.03 || vUv.y > 0.97)) {
    //     gl_FragColor = vec4( 1.0, 1.0, 1.0, 1.0 );
    // }

    if (gl_FragColor.a < 0.1) {
        if (backgroundOpacity == 0.0 || !debug)
            discard;
        else
            gl_FragColor = vec4(1.0, 1.0, 1.0, backgroundOpacity);
    }

}