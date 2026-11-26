"""Sinh file prompts/image-prompts.md: mỗi quote một prompt để dán vào Gemini (app, miễn phí).

Cách dùng: python scripts/make_image_prompts.py
Sau đó mở Gemini, đính kèm ảnh tham chiếu Ngựa ml (character sheet), dán từng prompt,
lưu ảnh thành docs/img/quote-01.png, quote-02.png... (đúng số id trong data/quotes.json).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = (
    "Giữ NGUYÊN nhân vật Ngựa ml như ảnh tham chiếu (cùng hình dáng, màu lông, mắt, phụ kiện). "
    "Phong cách {style}, nền pastel đơn giản, bố cục vuông 1:1, nhân vật ở giữa, chừa khoảng trống phía trên để chèn chữ. "
    "KHÔNG tự thêm chữ, logo hay watermark vào ảnh."
)


def main(style="2D cute sticker/chibi, nét viền mềm, tô màu phẳng"):
    quotes = json.loads((ROOT / "data/quotes.json").read_text(encoding="utf-8"))
    lines = ["# Prompt ảnh quote Ngựa ml\n", f"Phong cách chung: {style}\n"]
    for q in quotes:
        lines.append(f"## quote-{q['id']:02d}.png\n")
        lines.append(f"Quote: {q['text']}\n")
        lines.append(
            f"Prompt: Ngựa ml đang {q['action']}. Biểu cảm ngố, đáng yêu. {STYLE.format(style=style)}\n"
        )
    out = ROOT / "prompts/image-prompts.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Đã ghi {out} ({len(quotes)} prompt)")


if __name__ == "__main__":
    main()
