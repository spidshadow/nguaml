# Bản tin Ngựa ml

Bản tin 8h sáng trên điện thoại: tin esports/thể thao, lịch thi đấu, họp/email/task, quote Ngựa ml, joke.
Chạy tự động bằng GitHub Actions + Gemini API free, hiển thị bằng PWA, báo bằng web push. Chi phí hướng tới 0đ và không tốn usage Claude.

## Luồng hoạt động

```
07:40 (cron) -> build_brief.py
   |- Gemini + Google Search -> tin tức + lịch đấu   --> docs/brief/today.json (công khai, commit)
   |- Gemini -> joke (hoặc lấy từ data/jokes.json)
   |- chọn quote từ data/quotes.json (không lặp)
   |- Google/Outlook API -> họp, email, task           --> .private/private.json (KHÔNG commit)
 -> commit today.json -> chờ Pages -> send_push.py
 -> điện thoại nhận push, mở app. Phần riêng tư nằm trong payload mã hoá, lưu cục bộ trên máy.
```

Vì sao tách công khai/riêng tư: GitHub Pages của repo miễn phí là công khai. Tin tức, quote, joke không nhạy cảm nên để ở đó. Họp/email/task chỉ đi qua push đã mã hoá end-to-end tới máy bạn, không nằm trên repo.

## Cài đặt (khoảng 30 phút)

1. **Tạo repo GitHub** (public), đẩy toàn bộ thư mục này lên. Bật Pages: Settings > Pages > Deploy from branch > `main` / `/docs`.
2. **Sửa `config.json`**: `app_url` (địa chỉ Pages của bạn), `push_contact` (email của bạn), danh sách chủ đề.
3. **Gemini key**: lấy ở Google AI Studio, thêm secret `GEMINI_API_KEY`. Thêm variable `GEMINI_MODEL` (tên model Flash hiện hành, xem ai.google.dev/gemini-api/docs/models). Mặc định trong code là `gemini-2.5-flash`, nếu báo lỗi 404 thì đổi tên này.
4. **Khoá VAPID**: mở `https://<tên>.github.io/ban-tin-ngua/setup.html` trên máy tính, bấm "Tạo khoá". Dán khoá công khai vào `docs/config.js` rồi commit. Lưu khoá riêng vào secret `VAPID_PRIVATE_KEY`.
5. **Đăng ký điện thoại**: mở app trên điện thoại.
   - iPhone (iOS 16.4 trở lên): Safari > Chia sẻ > Thêm vào MH chính, rồi mở từ icon mới.
   - Android: Chrome > Cài đặt ứng dụng.
   - Bấm "Bật thông báo", vào Cài đặt > "Hiện mã đăng ký", sao chép vào secret `PUSH_SUBSCRIPTIONS`.
6. **Chạy thử**: tab Actions > daily-brief > Run workflow. Tick "dry run" để thử bằng dữ liệu mẫu trước (không gửi push), sau đó chạy thật.

## Nguồn riêng tư (làm sau khi bản cơ bản chạy ổn)

| Nguồn | Secret cần có | Ghi chú |
|---|---|---|
| Google Calendar, Gmail, Sheet | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | Tạo OAuth client trong Google Cloud, scope chỉ đọc: `calendar.readonly`, `gmail.readonly`, `spreadsheets.readonly`. Lấy refresh token bằng OAuth Playground. |
| Outlook / M365 | `MS_CLIENT_ID`, `MS_REFRESH_TOKEN` (+ `MS_CLIENT_SECRET`, var `MS_TENANT` nếu cần) | Đăng ký app trong Entra ID với quyền `Calendars.Read`, `Mail.Read`. Tài khoản công ty có thể bị admin chặn, cần kiểm tra trước. |
| Google Sheet checklist | điền `private.sheet` trong `config.json` | Khai đúng tên cột ngày, nội dung, trạng thái và định dạng ngày. |
| Slack | chưa làm | Làm được bằng Slack app + user token, để giai đoạn 2. |
| Zalo | không khả thi | Zalo cá nhân không có API chính thức để đọc tin nhắn. Nên chuyển các nhắc việc quan trọng sang Slack/email. |

Tắt nguồn nào không dùng bằng cách xoá khỏi `private.enabled_sources`.

## Ảnh quote Ngựa ml

Xem `prompts/ngua-ml-character.md`. Tóm tắt: tạo character sheet 1 lần, rồi render hàng loạt từ `prompts/image-prompts.md`, lưu vào `docs/img/quote-XX.png`. Muốn thêm quote: thêm một dòng vào `data/quotes.json` với `id` mới.

## Tối ưu usage

- Mỗi ngày chỉ 2 lần gọi Gemini (tin tức có Google Search, và joke). Quote lấy từ thư viện có sẵn, ảnh render trước nên không tốn gì mỗi sáng.
- Claude không tham gia vào lúc chạy hằng ngày. Chỉ dùng Claude khi bạn cần sửa code hoặc thêm tính năng.
- Joke lỗi thì tự rơi về `data/jokes.json`; tin tức lỗi thì app vẫn hiện quote và joke, không sập cả bản tin.

## Giới hạn cần biết

- **Độ chính xác lịch đấu**: lịch và tin do Gemini tìm qua Google Search, có thể sai hoặc thiếu. Với lịch LCP nên đối chiếu thêm trang chính thức; có thể nâng cấp sang nguồn API lịch thi đấu riêng ở giai đoạn sau.
- **Giờ chạy**: GitHub Actions có thể trễ vài chục phút so với cron. Nếu cần đúng 8:00, đặt cron sớm hơn.
- **iPhone**: push chỉ hoạt động khi app đã được thêm vào Màn hình chính.
- **Subscription hết hạn**: nếu push báo 404/410, bật lại thông báo trong app và cập nhật secret `PUSH_SUBSCRIPTIONS`.
- Repo public nên quote, tin, joke là công khai.
