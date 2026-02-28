importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

// Initialize the Firebase app in the service worker
// Use the exact same config as your boot file
firebase.initializeApp({
  apiKey: 'AIzaSyCmGRlXbGiaUr9otfEoBC1jZ9I17Ym_GWk',
  authDomain: 'adventure-board-40e02.firebaseapp.com',
  projectId: 'adventure-board-40e02',
  storageBucket: 'adventure-board-40e02.firebasestorage.app',
  messagingSenderId: '1065719539107',
  appId: '1:1065719539107:web:bb0adcf838091c104d2616',
  measurementId: 'G-ZKJ4BGQ9FX'
});

const messaging = firebase.messaging();

// This handles background notifications automatically
messaging.onBackgroundMessage((payload) => {
  console.log('Received background message ', payload);

  // Use payload.data instead of payload.notification
  const notificationTitle = payload.data.title || 'Adventure Board Update';
  const notificationOptions = {
    body: payload.data.body || '',
    icon: '/spelslot-logo.png', 
    data: {
      // Pulling from our custom data key
      clickUrl: payload.data.click_action || '/' 
    }
  };

  self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener('notificationclick', (event) =>{
    event.notification.close();

    // If click_action is "OPEN_APP", we use the root origin (e.g., signup.spelslot.nl)
    let targetUrl = event.notification.data?.clickUrl;
    if (targetUrl === 'OPEN_APP' || !targetUrl) {
      targetUrl = self.location.origin + '/#/'; 
    }

    event.waitUntil(
        clients.matchAll({type: 'window', includeUncontrolled: true}).then((windowClients) => {
            for (let client of windowClients) {
                if (client.url.includes(targetUrl) && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
