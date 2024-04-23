

const propBounds = {
    "x": [0, 1],
    "y": [0, 1]
}

export class Keyframe {
    constructor(time, props) {
        this.time = time;
        this.props = {};
        // this.dirtyProps = {};

        Object.keys(props).forEach((k) => this.addProperty(k, props[k]));
    }

    addProperty(key, value) {
        // Make sure property is within bounds
        if (key in propBounds) {
            value = Math.max(propBounds[key][0], Math.min(propBounds[key][1], value));
            // console.log("clamped value " + value);
        }

        // Add property or override existing
        this.props[key] = value;

        // Mark dirty
        // this.dirtyProps[key] = true;
    }

    removeProperty(key) {
        if (this.props.hasOwnProperty(key)) {
            delete this.props[key];
            return true;
        }
        return false;

        // Mark dirty
        // if (this.dirtyProps.hasOwnProperty(key)) {
        //     // delete this.dirtyProps[key];
        //     this.dirtyProps[key] = true;
        // }
    }

    clear() {
        Object.keys(this.props).forEach((k) => {
            this.removeProperty(k);
        });
    }

    isEmpty() {
        return Object.keys(this.props).length == 0;
    }

    // isDeletable() {
    //     return this.isEmpty() && Object.values(this.dirtyProps).every( f => !f);
    // }

    hasProperty(prop) {
        return this.props.hasOwnProperty(prop);
    }

    export() {
        return {
            time: this.time,
            props: JSON.parse(JSON.stringify(this.props)),
        }
    }

    // markClean() {
    //     Object.keys(this.dirtyProps).forEach((k) => this.dirtyProps[k] = false);
    // }

    // markDirty() {
    //     Object.keys(this.dirtyProps).forEach((k) => this.dirtyProps[k] = true);
    // }
    
}