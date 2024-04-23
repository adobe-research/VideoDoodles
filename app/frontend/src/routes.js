import {wrap} from 'svelte-spa-router/wrap'

import Homepage from './Homepage.svelte';
import App from './App.svelte';

export default {
    '/': Homepage,
    // '/about': About,
    '/app/:videoName': App,
    // The catch-all route must always be last
    // '*': NotFound
};