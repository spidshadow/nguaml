const CACHE = "ngua-ml-v1";
const SHELL = ["./", "index.html", "style.css", "app.js", "config.js", "manifest.webmanifest", "icons/icon-192.png"];

// ---- IndexedDB nhỏ để giữ phần riêng tư nhận từ push (không bao giờ lên server) ----
function idb() {
  return new Promise((res, rej) => {
    const r = indexedDB.open("ngua-ml", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("kv");
    r.onsuccess = () => res(r.result);
    r.onerror = () => rej(r.error);
  });
}
async function idbSet(key, value) {
  const db = await idb();
  return new Promise((res, rej) => {
    const tx = db.transaction("kv", "readwrite");
    tx.objectStore("kv").put(value, key);
    tx.oncomplete = res;
    tx.onerror = () => rej(tx.error);
  });
}

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  const isData = req.url.includes("/brief/");
  // Dữ liệu bản tin: ưu tiên mạng, rớt mạng mới dùng cache. Còn lại: cache trước.
  e.respondWith(
    isData
      ? fetch(req).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return r; })
          .catch(() => caches.match(req))
      : caches.match(req).then((hit) => hit || fetch(req).then((r) => {
          const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return r;
        }))
  );
});

self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch (_) { data = { title: "Bản tin Ngựa ml", body: e.data && e.data.text() }; }
  e.waitUntil((async () => {
    if (data.private) await idbSet("private", { date: data.date, ...data.private });
    await self.registration.showNotification(data.title || "Bản tin Ngựa ml", {
      body: data.body || "",
      icon: "icons/icon-192.png",
      badge: "icons/icon-192.png",
      tag: "daily-brief",
      data: { url: data.url || "./" },
    });
  })());
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "./";
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const c of list) if ("focus" in c) return c.focus();
      return clients.openWindow(url);
    })
  );
});
