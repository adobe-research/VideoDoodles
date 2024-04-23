#include <packing>

uniform sampler2D depthTexture;
uniform sampler2D colTexture;

varying vec2 vUv;

float worldToClip(float depth) {
    float nearPlane = 0.0005;
    float farPlane = 1000.0;
    return (1.0/depth - 1.0/nearPlane) / (1.0/farPlane - 1.0/nearPlane);
}

void main() {

    // gl_FragColor = vec4( vColor, 1.0 );

    float near = 0.05;
    float far = 5.0;

    float depth = texture2D(depthTexture, vUv).r;
    depth = viewZToOrthographicDepth(perspectiveDepthToViewZ( depth, near, far ), near, far);

    gl_FragColor = vec4(1.0 - depth, 1.0 - depth, 1.0 - depth, 1.0);

    // gl_FragColor = texture2D(colTexture, vUv);

}