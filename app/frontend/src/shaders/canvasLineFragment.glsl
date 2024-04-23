

uniform vec3 color;

varying vec2 vUv;

void main() {

    vec4 col = vec4(color, 1.0);
    gl_FragColor = col;

    if ( abs( vUv.y ) > 1.0 ) {
        float a = vUv.x;
        float b = ( vUv.y > 0.0 ) ? vUv.y - 1.0 : vUv.y + 1.0;
        float len2 = a * a + b * b;
        if ( len2 > 1.0 ) discard;
    }

}