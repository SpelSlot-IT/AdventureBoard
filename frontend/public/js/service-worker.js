self.addEventListener('push', (event) => {
  console.log(event);
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function (event) {
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data));
});

self.showNotification();

// When it's ready, check if there's a subscription already
const registration = await navigator.serviceWorker.ready;
let subscription = await registration.pushManager.getSubscription();
// If there's not, subscribe to the push notifications
if (subscription === null) {
  subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true, //Set user to see every notification
  });
  console.log(subscription);
}
console.log(subscription);
