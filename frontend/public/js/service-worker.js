self.addEventListener('push', (e) => {
  const data = e.data?.json() ?? {
    title: 'Adventure Board',
    desc: 'You have a new notification from SpelSlot',
  };

  e.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.desc,
      icon: '../spelslot-logo.svg',
    })
  );
});
