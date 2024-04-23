import { Float32BufferAttribute, BufferGeometry } from 'three';



export const generateGridGeometry = (segments) => {
    // From: https://github.com/mrdoob/three.js/blob/master/examples/webgl_buffergeometry_indexed.html

    const indices = [];
    const vertices = [];
    const uvs = [];

    const size = 2;
    const halfSize = size / 2;
    const segmentSize = size / segments;

    // generate vertices, normals and color data for a simple grid geometry
    for ( let i = 0; i <= segments; i ++ ) {
        const y = ( i * segmentSize ) - halfSize;
        for ( let j = 0; j <= segments; j ++ ) {

            const x = ( j * segmentSize ) - halfSize;
            vertices.push( x, -y, 0 );

            const u = ( j / (segments) );
            const v = 1 - ( i / (segments) );
            uvs.push( u, v );

            console.log(`${x}, ${y}, ${u}, ${v}`)
        }
    }

    for ( let iy = 0; iy < segments; iy ++ ) {

        for ( let ix = 0; ix < segments; ix ++ ) {

            const a = ix + (segments + 1) * iy;
            const b = ix + (segments + 1) * ( iy + 1 );
            const c = ( ix + 1 ) + (segments + 1) * ( iy + 1 );
            const d = ( ix + 1 ) + (segments + 1) * iy;

            indices.push( a, b, d );
            indices.push( b, c, d );

        }

    }
    // console.log(indices);

    // console.log(vertices.length);

    const geometry = new BufferGeometry();
    geometry.setIndex( indices );
    geometry.setAttribute( 'position', new Float32BufferAttribute( vertices, 3 ) );
    geometry.setAttribute( 'uv', new Float32BufferAttribute( uvs, 2 ) );

    return geometry
}

export const generateGridCoordinates = (segments, size) => {
    const vertices = [];

    // const halfSize = size / 2;
    const segmentSize = size / segments;

    // generate vertices, normals and color data for a simple grid geometry
    // let idx = 0;
    for ( let i = 0; i <= segments; i ++ ) {
        const y = ( i * segmentSize );
        for ( let j = 0; j <= segments; j ++ ) {

            const x = ( j * segmentSize );
            vertices.push( {x: x, y: y, xIdx: j, yIdx: i} );
            // idx ++;
        }
    }

    // for ( let i = 0; i <= segments; i ++ ) {
    //     const y = ( i * segmentSize ) - halfSize;
    //     for ( let j = 0; j <= segments; j ++ ) {

    //         const x = ( j * segmentSize ) - halfSize;
    //         vertices.push( x, -y, 0 );

    //         const u = ( j / (segments) );
    //         const v = 1 - ( i / (segments) );
    //         uvs.push( u, v );

    //         console.log(`${x}, ${y}, ${u}, ${v}`)
    //     }
    // }

    return vertices;

}