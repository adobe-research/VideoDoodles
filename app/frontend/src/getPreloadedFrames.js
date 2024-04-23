
import Frame from './Frame.js';



// export const allFrames = [];

export const getPreloadedFrames = (file, frameCount) => {
    const allFrames = [];

    for (let i = 0; i <= frameCount - 1; i++) {
        let frameDir = "batch" + String(i).padStart(4, 0);
        allFrames.push(new Frame(file, frameDir, i));
    }

    return allFrames;
}