
// attribute vec3 position;

varying vec2 clipPos;

void main() {
    // gl_Position =  vec4( position, 1.0 );
    gl_Position =  vec4( position.x, position.y, 0.0, 1.0 );

    clipPos = vec2(position.x, position.y);
}