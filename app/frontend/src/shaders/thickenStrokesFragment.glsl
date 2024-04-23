
uniform sampler2D sceneColorBuffer;
uniform sampler2D strokesBuffer;
uniform vec2 pixelSize;
uniform int gatherRadius;

varying vec2 vUv;


vec4 getPixelStrokeColor(int x, int y) {
    // screenSize.zw is pixel size 
    // vUv is current position
    return texture2D(strokesBuffer, vUv + pixelSize * vec2(x, y));
}

void main() {
    vec4 sceneColor = texture2D(sceneColorBuffer, vUv);

    // Sample neighboring pixels
    vec4 sum = vec4( 0.0, 0.0, 0.0, 0.0 );
    // vec2 relCoord = vec2(0, 0);
    int assignedPixelsCount = 0;

    for( int i = -gatherRadius; i <= gatherRadius; i ++ ) {
        for (int j = -gatherRadius; j <= gatherRadius; j++) {
            if (i != 0 || j != 0) {
                vec4 pixColor = getPixelStrokeColor( i, j );
                // sum += pixColor;
                if (pixColor.a > 0.0) {
                    assignedPixelsCount++;
                }
                sum = vec4(mix(sum, pixColor, pixColor.a));
            }
        }
    }

    int size = 2 * gatherRadius + 1;

    // float alpha = sum.a;
    // vec3 sketchCol = sum.rgb;

    // sketchCol /= float(assignedPixelsCount);

    float alpha = 0.0;
    if (assignedPixelsCount > 0) {
        alpha = 1.0;
    }

    // Combine outline with scene color.
    vec4 outlineColor = vec4(1.0, 0.0, 0.0, 1.0);
    gl_FragColor = vec4(mix(sceneColor, sum, alpha));

    // gl_FragColor = vec4(1.0 ,0.0 ,0.0, 1.0);
    // gl_FragColor = sceneColor;

    // gl_FragColor = texture2D(strokesBuffer, vUv);
}

