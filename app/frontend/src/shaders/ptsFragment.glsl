

varying vec3 vColor;

// float worldToClip(float depth) {
//     float nearPlane = 0.0005;
//     float farPlane = 100000000.0;
//     return (1.0/depth - 1.0/nearPlane) / (1.0/farPlane - 1.0/nearPlane);
// }

void main() {


    if ( length( gl_PointCoord - vec2( 0.5, 0.5 ) ) > 0.475 ) discard;

    float distToBorder = 0.475 - length( gl_PointCoord - vec2( 0.5, 0.5 ) );

    gl_FragColor = vec4( vColor, 1.0 );


    // gl_FragColor = vec4(worldToClip(gl_FragCoord.z) * 0.5 + 0.5, 0.0, 0.0, 1.0);

}