import { boot } from 'quasar/wrappers';
import { ref, App } from 'vue';
import { isAxiosError } from 'axios';
import { Notify } from 'quasar';
import { capitalize } from '../util/common';

const errorHandler = (error: unknown, app: App<any>) => {
	const errorMessages = extractErrors(error, app);
	for(const e of errorMessages) {
		Notify.create({
			message: capitalize(e),
			position: 'top',
			type: 'negative',
		});
	}
};

function extractErrors(error: unknown, app: App<any>): string[] {
	console.log(error);
	let errorMessages: string[] = [];
	if(isAxiosError(error)) {
		if(error.response?.status == 401) {
			// This is watched by the MainLayout and triggers a logout.
			app.config.globalProperties.$notLoggedInError.value = true;
			return ['You\'re not logged in'];
		}
		if(error.response?.data?.errors?.length > 0) {
			errorMessages = errorMessages.concat(error.response!.data!.errors);
		}
	}
	if(errorMessages.length == 0) {
		return ['An internal error occurred. Please reload the page and contact us if the problem persists.'];
	}
	return errorMessages;
};

export default boot(({ app }) => {
	app.config.errorHandler = (error) => {
		errorHandler(error, app);
	};
	app.config.globalProperties.$notLoggedInError = ref(false);
	app.config.globalProperties.$extractErrors = (error: unknown) => extractErrors(error, app);

	window.addEventListener('unhandledrejection', function(event) {
		errorHandler(event.reason, app);
	}, {passive: true});
});
