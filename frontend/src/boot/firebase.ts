import { boot } from 'quasar/wrappers';
import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, Messaging } from 'firebase/messaging';

// 1. Get these values from your Firebase Console:
// Project Settings > General > Your Apps (Web App)
const firebaseConfig = {
  apiKey: 'AIzaSyCmGRlXbGiaUr9otfEoBC1jZ9I17Ym_GWk',
  authDomain: 'adventure-board-40e02.firebaseapp.com',
  projectId: 'adventure-board-40e02',
  storageBucket: 'adventure-board-40e02.firebasestorage.app',
  messagingSenderId: '1065719539107',
  appId: '1:1065719539107:web:bb0adcf838091c104d2616',
  measurementId: 'G-ZKJ4BGQ9FX'
};

// 2. Initialize Firebase
const firebaseApp = initializeApp(firebaseConfig);
const messaging = getMessaging(firebaseApp);

// 3. Extend the Vue interface so TypeScript knows about $messaging
declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $messaging: Messaging;
  }
}

export default boot(({ app }) => {
  // This makes this.$messaging available in all your components
  app.config.globalProperties.$messaging = messaging;
});

// We export these for direct use in the component logic
export { messaging, getToken };