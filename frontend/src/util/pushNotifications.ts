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
    };
    return true;
}

export async function setupNotifications() {
    try {
        if (!checkBrowserSupport()) {
            throw new Error('Push notifications arent supported in this browser. Tough luck, bucko.');
        }
        const havePermission = await handleNotifications();
        if (!havePermission) {
            throw new Error('We don\'t have the required permissions. Not our fault')
        }
        
        // register the SW
        const path = '/js/service-worker.js';
        await navigator.serviceWorker.register(path);
    } catch (err) {
        window.alert(err);
    }
}