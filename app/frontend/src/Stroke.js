import { Matrix4, Vector2, Vector3, InstancedInterleavedBuffer, InstancedBufferGeometry, Float32BufferAttribute, InterleavedBufferAttribute, Mesh, ShaderMaterial, DoubleSide, Object3D, Line } from 'three';

import * as d3 from "d3";


import vertexShader from './shaders/canvasLineVertex.glsl';
import fragmentShader from './shaders/canvasLineFragment.glsl';


const lineMat = new ShaderMaterial({
    uniforms :{
        canvasPos: { value: new Vector3() },
        canvasRot: { value: new Matrix4() },
        canvasScale: { value: 1.0 },
        lineWidth: { value: 0.02 },
        // aspect: { value: 1.0 },
        color: { value: new Vector3(1.0, 0.0, 0.0) },
    },
    vertexShader : vertexShader,
    fragmentShader : fragmentShader,
    side: DoubleSide,
    transparent: true,
    depthWrite: false,
    // wireframe: true
    // alphaTest: 0.8
});

const lineMatOccluder = new ShaderMaterial({
    uniforms :{
        canvasPos: { value: new Vector3() },
        canvasRot: { value: new Matrix4() },
        canvasScale: { value: new Vector2(1.0, 1.0) },
        lineWidth: { value: 0.02 },
        color: { value: new Vector3(1.0, 0.0, 0.0) },
    },
    vertexShader : vertexShader,
    fragmentShader : fragmentShader,
    side: DoubleSide,
    transparent: true,
    depthWrite: true,
    colorWrite: false,
    // wireframe: true
    // alphaTest: 0.8
});

// const lineMat = new LineMaterial({

//     color: 0x808080,
//     linewidth: 5, // in world units with size attenuation, pixels otherwise
//     vertexColors: false,

//     //resolution:  // to be set by renderer, eventually
//     dashed: false,
//     alphaToCoverage: true,

// } );

// console.log(lineMat);

class LineSegmentsGeometry extends InstancedBufferGeometry {
    constructor() {
        super();
        // this.object.renderOrder = 5;

        const positions = [ - 1, 2, 0, 1, 2, 0, - 1, 1, 0, 1, 1, 0, - 1, 0, 0, 1, 0, 0, - 1, - 1, 0, 1, - 1, 0 ];
		const uvs = [ - 1, 2, 1, 2, - 1, 1, 1, 1, - 1, - 1, 1, - 1, - 1, - 2, 1, - 2 ];
		const index = [ 0, 2, 1, 2, 3, 1, 2, 4, 3, 4, 5, 3, 4, 6, 5, 6, 7, 5 ];

		this.setIndex( index );
		this.setAttribute( 'position', new Float32BufferAttribute( positions, 3 ) );
		this.setAttribute( 'uv', new Float32BufferAttribute( uvs, 2 ) );

    }

    // Positions defined in canvas space [0,1]x[0,1]
    // array = [ x1 y1 x2 y2 x3 y3 ... ]
    setPositions( array ) {

		let lineSegments;

		if ( array instanceof Float32Array ) {

			lineSegments = array;

		} else if ( Array.isArray( array ) ) {

			lineSegments = new Float32Array( array );

		}

		const instanceBuffer = new InstancedInterleavedBuffer( lineSegments, 4, 1 ); // xyz, xyz
        // instanceBuffer.needsUpdate = true;

		this.setAttribute( 'instanceStart', new InterleavedBufferAttribute( instanceBuffer, 2, 0 ) ); // xy
		this.setAttribute( 'instanceEnd', new InterleavedBufferAttribute( instanceBuffer, 2, 2 ) ); // xy

        // console.log(this.getAttribute('instanceStart'));

        // this.attributes.instanceStart.data.onUpload(() => console.log("uploaded instanceStart buffer"));

        // this.attributes.instanceStart.needsUpdate = true;
        // this.attributes.instanceEnd.needsUpdate = true;
        // console.log(this.attributes.instanceStart);

	}

    // Returns a Float32Array [ x1 y1 x2 y2 x3 y3 ... ]
    // This is not a copy, so probably I shouldn't mess with it...
    getPositions() {
        return this.getAttribute('instanceStart').data.array;
    }

    addPoints( pts ) {
        // Previous points
        const allPointsArray = Array.from(this.getAttribute('instanceStart').data.array);

        pts.forEach((pt) => {
            allPointsArray.push(pt.x, pt.y);
        });

        this.setPositions(allPointsArray);
    }
}

export default class Stroke {
    constructor(strokeID, canvasID) {
        // Copying shader so that we can change uniforms
        this.material = lineMat.clone();
        this.occluderMaterial = lineMatOccluder.clone();

        // this.ID = `${canvasID}-${strokeID}`;
        this.strokeID = strokeID;
        this.canvasID = canvasID;
        this.selected = false;

        this.geometry = new LineSegmentsGeometry();
        this.object = new Mesh(this.geometry,  this.material );
        this.object.frustumCulled = false;
        this.object.renderOrder = 100 + canvasID;
        // console.log("render order :" + this.object.renderOrder)

        this.occObject = new Mesh(this.geometry,  this.occluderMaterial );
        this.occObject.frustumCulled = false;
        this.occObject.renderOrder = 100 + canvasID + 1;
        // renderOrder += 2;
        // console.log("render order :" + this.occObject.renderOrder)
        // this.object.layers.enable(1);

        this.object.type = "Stroke";
        

        this.geometry.setPositions([]);
    }

    get ID() {
        return `${this.canvasID}-${this.strokeID}`;
    }

    setColor( color ) {
        this.material.uniforms.color.value = new Vector3(color.r, color.g, color.b);
    }

    setRadius( radius ) {
        this.material.uniforms.lineWidth.value = radius;
        this.occluderMaterial.uniforms.lineWidth.value = radius;
    }

    addPoints( points ) {
        this.geometry.addPoints(points);;

    }

    addTo(parent) {
        parent.add(this.object);
        parent.add(this.occObject);
    }

    setCanvasPosition( vec ) {
        this.material.uniforms.canvasPos.value = vec;
        this.occluderMaterial.uniforms.canvasPos.value = vec;
    }

    setCanvasRotation( rotMat ) {
        this.material.uniforms.canvasRot.value = rotMat;
        this.occluderMaterial.uniforms.canvasRot.value = rotMat;
    }

    setCanvasScale( scale ) {
        this.material.uniforms.canvasScale.value = scale;
        this.occluderMaterial.uniforms.canvasScale.value = scale;
    }

    drawGizmo(svg, interactable=true, color=undefined) {
        const positionArray = this.geometry.getPositions();
        const ptsCount = positionArray.length / 2;

        // console.log(`stroke ${this.ID} has ${ptsCount} pts`);

        let points = []
        for (let i = 0; i < ptsCount; i++) {
            let x = (1 + positionArray[i * 2]) * 0.5 * svg.attr("width");
            let y = (1 + positionArray[i * 2 + 1]) * 0.5 * svg.attr("height");
            points.push([x, y]);
        }

        svg.selectAll(`path#stroke-${this.ID}`).remove();

        const self = this;
        this.gizmo = svg.append("path")
            .datum(points)
            .attr("id", `stroke-${this.ID}`)
            .attr("fill", "none")
            .attr("stroke", color ? color : (self.selected ? "red" : "steelblue"))
            // .attr("opacity", 0.5)
            .attr("stroke-width", 0.03 * svg.attr("width"))
            .attr('stroke-linecap', "round")
            .attr('stroke-linejoin', "round")
            .attr("d", d3.line()
                    .x(d => d[0])
                    .y(d => d[1])
                    )
        if (interactable) {
            this.gizmo
                .on("mouseover", (e, d) => {
                    // console.log("hovering stroke " + self.ID);
                    d3.select(`path#stroke-${this.ID}`).attr("stroke", "yellow");
                })
                .on("mouseout", (e, d) => {
                    // console.log("hovering stroke " + self.ID);
                    d3.select(`path#stroke-${this.ID}`).attr("stroke", self.selected ? "red" : "steelblue");
                })
                .on("click", (e, d) => {
                    self.selected = !self.selected;
                    d3.select(`path#stroke-${this.ID}`).attr("stroke", self.selected ? "red" : "steelblue");
                })
        }
        

        return this.gizmo;
    }

    delete() {
        this.geometry.dispose();
        this.material.dispose();
        this.occluderMaterial.dispose();
        this.object.removeFromParent();
        if (this.gizmo)
            this.gizmo.remove();
    }

    export () {
        return {
            strokeID: this.strokeID,
            canvasID: this.canvasID,
            points: Array.from(this.geometry.getPositions()),
            color: this.material.uniforms.color.value,
            radius: this.material.uniforms.lineWidth.value
        }
    }
}