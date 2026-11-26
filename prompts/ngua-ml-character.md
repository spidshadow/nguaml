# Tạo nhân vật Ngựa ml bằng Gemini

Mục tiêu: có 1 "character sheet" cố định, rồi dùng nó làm ảnh tham chiếu cho cả 30+ ảnh quote để nhân vật không bị lệch.

## Bước 1: chụp ảnh gốc
Chụp Ngựa ml bông thật: 1 ảnh chính diện, 1 ảnh nghiêng, 1 ảnh cận mặt, nền sáng, đủ sáng.

## Bước 2: tạo character sheet 2D (đính kèm 3 ảnh trên)
```
Dựa trên con ngựa bông trong ảnh, hãy tạo character sheet 2D phong cách sticker chibi dễ thương.
Giữ đúng: màu lông, hình dáng tai, mắt, bờm, phụ kiện, họa tiết của con ngựa bông gốc.
Gồm 6 góc/biểu cảm trên cùng một tờ: đứng chính diện, nghiêng, ngồi, ngủ gật, cười ngố, ngạc nhiên.
Nền trắng trơn, nét viền mềm, tô màu phẳng, không chữ, không watermark.
```

## Bước 3: nếu muốn bản 3D
```
Từ character sheet này, tạo ảnh nhân vật 3D kiểu đồ chơi vải bông (plush render),
chất liệu lông mềm, ánh sáng studio dịu, nền pastel, chính diện toàn thân.
```
Chọn MỘT phong cách (2D hoặc 3D) cho cả series, đừng trộn.

## Bước 4: render hàng loạt
1. Chạy `python scripts/make_image_prompts.py` để sinh `prompts/image-prompts.md`.
2. Trong Gemini, mở chat mới, đính kèm character sheet đã chốt, dán từng prompt.
3. Lưu ảnh thành `docs/img/quote-01.png`, `quote-02.png`... đúng số trong tên mục.
4. Mẹo giữ nhân vật nhất quán: mỗi 8-10 ảnh mở chat mới và đính kèm lại character sheet; nên render trong cùng một phiên nếu có thể.
5. Nén ảnh về khoảng 800x800 (dưới 200KB/ảnh) để PWA tải nhanh và repo không phình to (tinypng.com hoặc Squoosh).

Ảnh thiếu file thì app tự hiện hình 🐴 thay thế, nên có thể render dần.
