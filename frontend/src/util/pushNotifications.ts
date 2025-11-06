async function getPublicVapid() {
  const response = await fetch('/api/push/vapid-public-key');
  const json = await response.json();
  return json.public_key;
}

async function handleNotifications(): Promise<boolean> {
  if (Notification.permission === 'denied') {
    return false;
  }

  if (Notification.permission !== 'granted') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
  return true;
}

function checkBrowserSupport(): boolean {
  if (!('Notification' in window)) {
    return false;
    // throw new Error('Browser does not support notifications');
  }
  if (!('PushManager' in window)) {
    return false;
    // throw new Error('Sorry, Push notification isn\'t supported in your browser.');
  }
  if (!('serviceWorker' in navigator)) {
    return false;
    // throw new Error('Browser does not support service workers');
  }
  return true;
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export async function setupNotifications() {
  try {
    if (!checkBrowserSupport()) {
      throw new Error(
        'Push notifications arent supported in this browser. Tough luck, bucko.'
      );
    }
    const havePermission = await handleNotifications();
    if (!havePermission) {
      throw new Error("We don't have the required permissions. Not our fault");
    }

    // register the SW
    const path = '/js/service-worker.js';
    const register = await navigator.serviceWorker.register(path);
    const publicVAPID = await getPublicVapid();

    const subscription = await register.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicVAPID),
    });

    // Subscribe to the API
    await fetch('/api/push/subscribe', {
      method: 'POST',
      body: JSON.stringify(subscription),
      headers: {
        'content-type': 'application/json',
      },
    });
  } catch (err) {
    window.alert(err);
  }
}
