import Main from './Main.svelte';


const app = new Main({
	target: document.body,
	props: {
	}
});


window.app = app;

export default app;