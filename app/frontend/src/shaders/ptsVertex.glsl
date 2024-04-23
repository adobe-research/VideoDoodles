uniform float size;
attribute vec3 color;

varying vec3 vColor;

void main() {

    vColor = color;

    vec4 mvPosition = modelViewMatrix * vec4( position, 1.0 );

    gl_PointSize = size;

    gl_Position = projectionMatrix * mvPosition;

}