self.addEventListener("push", function(event) {
  var payload = event.data ? event.data.text() : "no payload";
  event.waitUntil(
    self.registration.showNotification("Alfred Notification", {
      body: payload,
      icon: "/static/img/logo_48.png"
    })
  );
});

self.addEventListener('install', function(event) {
  // Perform install steps
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll([
            "/",
            "/static/css/base.css",
            "/static/js/base.js",
            "/static/js/jquery-3.2.1.min.js",
            "/static/img/logo_192.png"
        ]);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request, {ignoreSearch:true}).then(response => {
      return response || fetch(event.request);
    })
  );
});