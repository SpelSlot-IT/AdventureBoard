self.addEventListener('push', (e) => {
  const data = e.data.json();
  self.registration.showNotification(data.title, {
    body: data.desc ?? 'You have a new notification from SpelSlot',
    icon: '',
  });
});
