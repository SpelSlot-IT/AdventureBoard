import { QVueGlobals } from 'quasar';
import { boot } from 'quasar/wrappers';
import axios, { AxiosInstance } from 'axios';

declare module '@vue/runtime-core' {
	interface ComponentCustomProperties {
		$q: QVueGlobals;
		$api: AxiosInstance;
		$extractErrors(error: unknown): string[];
	}
}

export default boot(({ app }) => {
	// for use inside Vue files (Options API) through this.$api

	// Be careful when using SSR for cross-request state pollution
	// due to creating a Singleton instance here;
	// If any client changes this (global) instance, it might be a
	// good idea to move this instance creation inside of the
	// "export default () => {}" function below (which runs individually
	// for each client)
	const api = axios.create({});

	app.config.globalProperties.$api = api;
});
