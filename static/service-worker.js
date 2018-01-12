self.addEventListener('push', function(event) {
  var payload = event.data ? event.data.text() : 'no payload';
  event.waitUntil(
    self.registration.showNotification('Alfred Notification', {
      body: payload,
    })
  );
});