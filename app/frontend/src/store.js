import { writable } from 'svelte/store';

export const message = writable("");
export const criticalErrorMessage = writable("");
export const availableClips = writable([]);
export const clipName = writable("");
export const clipFrames = writable([]);

export const time = writable(0);

export const dialogProps = writable({});