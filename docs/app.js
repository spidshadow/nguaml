// Giao diện bản tin. Mọi nội dung chèn vào DOM đều qua textContent để tránh XSS.
const $ = (s) => document.querySelector(s);
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null) el.append(kid.nodeType ? kid : document.createTextNode(kid));
  return el;
}
const card = (title, ...kids) => h("section", { class: "card" }, h("h2", {}, title), ...kids);

function idbGet(key) {
  return new Promise((res) => {
    const r = indexedDB.open("ngua-ml", 1);
    r.onupgradeneeded = () => r.result.createObjectStore("kv");
    r.onsuccess = () => {
      const g = r.result.transaction("kv").objectStore("kv").get(key);
      g.onsuccess = () => res(g.result || null);
      g.onerror = () => res(null);
    };
    r.onerror = () => res(null);
  });
}

function renderQuote(q) {
  const media = q.image
    ? h("img", { class: "quote-img", src: q.image, alt: "Ngựa ml: " + q.action, loading: "lazy" })
    : h("div", { class: "quote-fallback", "aria-hidden": "true" }, "🐴");
  return h("section", { class: "card quote-card" }, media,
    h("div", { class: "quote-body" },
      h("p", { class: "quote-text" }, q.text),
      h("p", { class: "quote-action" }, "Ngựa ml đang " + q.action)));
}

function renderPrivate(p, briefDate) {
  if (!p) return card("Việc hôm nay của bạn", h("p", { class: "private-empty" },
    "Chưa có dữ liệu. Phần này hiện sau khi nhận thông báo 8h sáng trên máy này."));
  const stale = p.date && p.date !== briefDate;
  const rows = [];
  p.meetings?.forEach((m) => rows.push(h("div", { class: "item" },
    h("span", { class: "time" }, m.time), h("span", { class: "title" }, m.title), h("div", { class: "sub" }, m.source))));
  p.emails?.forEach((m) => rows.push(h("div", { class: "item" },
    h("span", { class: "tag" }, "Email"), h("span", { class: "title" }, m.subject), h("div", { class: "sub" }, m.from + " · " + m.source))));
  p.tasks?.forEach((t) => rows.push(h("div", { class: "item" },
    h("span", { class: "tag" }, "Task"), h("span", { class: "title" }, t.title), h("div", { class: "sub" }, "Hạn " + t.due + " · " + t.source))));
  return card("Việc hôm nay của bạn",
    stale ? h("div", { class: "warn" }, "Dữ liệu này của ngày " + p.date + ", chưa cập nhật cho hôm nay.") : null,
    rows.length ? rows : h("p", { class: "private-empty" }, "Hôm nay không có họp, email quan trọng hay task đến hạn."));
}

function render(d, priv) {
  $("#date").textContent = d.date_label;
  const app = $("#app");
  app.replaceChildren(
    renderQuote(d.quote),
    renderPrivate(priv, d.date),
    card("Lịch thi đấu hôm nay",
      d.schedule.length
        ? d.schedule.map((s) => h("div", { class: "item" }, h("span", { class: "time" }, s.time),
            h("span", { class: "title" }, s.match), h("div", { class: "sub" }, s.league)))
        : h("p", { class: "private-empty" }, d.news_failed ? "Không lấy được lịch hôm nay." : "Hôm nay chưa có trận nào được xác nhận.")),
    card("Tin sáng",
      d.headlines.length
        ? d.headlines.map((n) => h("div", { class: "item" }, h("span", { class: "tag" }, n.category),
            h("span", { class: "title" }, n.title), h("div", { class: "sub" }, n.summary + (n.source ? " (" + n.source + ")" : ""))))
        : h("p", { class: "private-empty" }, "Chưa lấy được tin hôm nay.")),
    card("Joke of the day", h("p", { class: "joke" }, d.joke)),
    d.sources?.length
      ? h("div", { class: "sources" }, d.sources.map((s) => h("a", { href: s.url, target: "_blank", rel: "noopener noreferrer" }, s.title || "nguồn")))
      : null
  );
  $("#updated").textContent = "Cập nhật: " + new Date(d.generated_at).toLocaleString("vi-VN");
}

// ---- Push ----
function b64urlToUint8(s) {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}
async function enablePush() {
  const btn = $("#btn-push");
  try {
    if (!("serviceWorker" in navigator) || !("PushManager" in window))
      throw new Error("Trình duyệt chưa hỗ trợ push. Trên iPhone: Chia sẻ > Thêm vào MH chính, rồi mở app từ icon.");
    const key = (window.APP_CONFIG || {}).VAPID_PUBLIC_KEY || localStorage.getItem("vapid_pub");
    if (!key) throw new Error("Chưa có VAPID_PUBLIC_KEY. Vào Cài đặt để tạo khoá.");
    if ((await Notification.requestPermission()) !== "granted") throw new Error("Bạn chưa cho phép thông báo.");
    const reg = await navigator.serviceWorker.ready;
    const sub = (await reg.pushManager.getSubscription()) ||
      (await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64urlToUint8(key) }));
    localStorage.setItem("push_sub", JSON.stringify(sub));
    btn.textContent = "Đã bật. Xem mã đăng ký ở Cài đặt";
    btn.disabled = true;
  } catch (e) {
    alert(e.message);
  }
}

async function init() {
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(console.warn);
  $("#btn-push").addEventListener("click", enablePush);
  if (localStorage.getItem("push_sub")) { $("#btn-push").textContent = "Đã bật. Xem mã đăng ký ở Cài đặt"; $("#btn-push").disabled = true; }
  try {
    const r = await fetch("brief/today.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    render(await r.json(), await idbGet("private"));
  } catch (e) {
    $("#app").replaceChildren(card("Chưa có bản tin", h("p", { class: "private-empty" },
      "Chưa tải được bản tin hôm nay. Thử mở lại khi có mạng, hoặc chạy workflow trên GitHub lần đầu.")));
  }
}
init();
