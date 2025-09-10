import { boot } from 'quasar/wrappers';
import { isAxiosError } from 'axios';
import { Notify } from 'quasar';
import { capitalize } from '../util/common';

const errorHandler = (error: unknown) => {
  const errorMessages = extractErrors(error);
  for (const e of errorMessages) {
    Notify.create({
      message: capitalize(e),
      position: 'top',
      type: 'negative',
    });
  }
};

function extractErrors(error: unknown): string[] {
  console.log(error);
  const errorMessages: string[] = [];
  if (isAxiosError(error)) {
    if (error.response?.status == 401) {
      return ["You're not logged in"];
    }
    if (error.response?.data?.message) {
      errorMessages.push(error.response!.data!.message);
    }
    if (error.response?.data?.error) {
      errorMessages.push(error.response!.data!.error);
    }
  }
  if (errorMessages.length == 0) {
    return [
      'An internal error occurred. Please reload the page and contact us if the problem persists.',
    ];
  }
  return errorMessages;
}

export default boot(({ app }) => {
  app.config.errorHandler = errorHandler;
  app.config.globalProperties.$extractErrors = extractErrors;

  window.addEventListener(
    'unhandledrejection',
    function (event) {
      errorHandler(event.reason);
    },
    { passive: true }
  );
});
