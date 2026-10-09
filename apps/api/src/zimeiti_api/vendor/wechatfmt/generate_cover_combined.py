"""微信公众号拼接封面图生成器

vendor 来源：E:/Projects/my-tools/wechat-mp-manage/src/wechat_mp_manage/article_manage/generate_cover_combined.py
（上游未改动）

生成一张包含两种封面的拼接图：
  - 上半部分：1:1 方封面（二级结构：子分类 + 标题，居中）
  - 下半部分：2.35:1 宽封面（三级结构：系列名 + 子分类 + 标题）

上传到微信后台后，方封面区域裁上半部分，宽封面区域裁下半部分。

用法:
  python generate_cover_combined.py <title> --sub <子分类> [--series <系列名>] [--theme <主题>] [--output <路径>]

示例:
  python generate_cover_combined.py "认识大语言模型" --sub "LLM 基础"
  python generate_cover_combined.py "Agent 循环" --sub "Agent 循环" --theme midnight
"""

import argparse
import os
import random
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise ImportError("需要 Pillow: pip install Pillow")

# ─── 尺寸 ─────────────────────────────────────────────────────────
WIDE_W, WIDE_H = 900, 383
SQUARE_SIZE = 900
TOTAL_W = WIDE_W
TOTAL_H = WIDE_H + SQUARE_SIZE  # 1283

# ─── 主题配色 ─────────────────────────────────────────────────────
THEMES = {
    "aurora": {
        "bg_top": (18, 22, 48), "bg_bot": (28, 35, 65),
        "accent": (100, 180, 255),
        "card": (255, 255, 255, 18),
        "card_border": (100, 180, 255, 40),
        "text": (255, 255, 255), "sub": (160, 190, 230),
    },
    "ocean": {
        "bg_top": (12, 30, 55), "bg_bot": (18, 55, 90),
        "accent": (50, 200, 230),
        "card": (255, 255, 255, 15),
        "card_border": (50, 200, 230, 35),
        "text": (255, 255, 255), "sub": (140, 210, 235),
    },
    "midnight": {
        "bg_top": (20, 18, 42), "bg_bot": (35, 28, 60),
        "accent": (150, 120, 255),
        "card": (255, 255, 255, 16),
        "card_border": (150, 120, 255, 35),
        "text": (255, 255, 255), "sub": (190, 175, 240),
    },
    "sunset": {
        "bg_top": (42, 18, 38), "bg_bot": (70, 30, 45),
        "accent": (255, 150, 80),
        "card": (255, 255, 255, 16),
        "card_border": (255, 150, 80, 35),
        "text": (255, 255, 255), "sub": (240, 190, 160),
    },
    "forest": {
        "bg_top": (14, 32, 28), "bg_bot": (20, 55, 45),
        "accent": (70, 220, 150),
        "card": (255, 255, 255, 15),
        "card_border": (70, 220, 150, 35),
        "text": (255, 255, 255), "sub": (150, 230, 195),
    },
}


# ─── 工具函数 ─────────────────────────────────────────────────────

def _lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def _title_font_size(title_text: str, base: int = 72) -> int:
    """根据标题长度计算字号"""
    n = len(title_text)
    if n <= 6:
        return base
    elif n <= 8:
        return int(base * 0.72)
    elif n <= 10:
        return int(base * 0.72)
    elif n <= 14:
        return int(base * 0.67)
    elif n <= 18:
        return int(base * 0.56)
    else:
        return int(base * 0.47)


def _find_font(size):
    if sys.platform == "win32":
        candidates = [
            os.path.expandvars(r"%WINDIR%\Fonts\msyhbd.ttc"),
            os.path.expandvars(r"%WINDIR%\Fonts\msyh.ttc"),
            os.path.expandvars(r"%WINDIR%\Fonts\simhei.ttf"),
        ]
    elif sys.platform == "darwin":
        candidates = ["/System/Library/Fonts/PingFang.ttc"]
    else:
        candidates = ["/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]
    for fp in candidates:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def _find_break_point(text):
    """在文本中查找最后一个空格位置，用于英文单词不断裂。

    Returns:
        (line, rest): line 为当前行文本，rest 为下一行起始文本。
        若找不到空格，则按字符级断裂。
    """
    for i in range(len(text) - 1, -1, -1):
        if text[i] == ' ':
            return text[:i + 1], text[i + 1:]
    # 无空格（纯中文或单个英文单词），强制在末尾断裂
    return text, ""


def _wrap_text(draw, text, font, max_width):
    """将文本按最大宽度自动换行，英文单词不会断裂"""
    lines = []
    cur = ""
    for ch in text:
        test = cur + ch
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > max_width and cur:
            line_part, rest = _find_break_point(cur)
            lines.append(line_part.rstrip(' '))
            cur = rest + ch
        else:
            cur = test
    if cur:
        lines.append(cur.rstrip(' '))
    return lines


# ─── 通用绘制 ─────────────────────────────────────────────────────

def _draw_bg(img, w, h, theme):
    """绘制渐变背景"""
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        c = _lerp_color(theme["bg_top"], theme["bg_bot"], t)
        draw.line([(0, y), (w, y)], fill=c)


def _draw_glow(img, w, h, theme):
    """绘制光晕"""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    accent = theme["accent"]

    cx, cy, r = w - int(w * 0.13), int(h * 0.16), int(w * 0.24)
    for i in range(30, 0, -1):
        ri = int(r * i / 30)
        alpha = int(12 * (1 - i / 30))
        od.ellipse([cx - ri, cy - ri, cx + ri, cy + ri], fill=(*accent, alpha))

    cx2, cy2, r2 = int(w * 0.09), h - int(h * 0.13), int(w * 0.18)
    for i in range(20, 0, -1):
        ri = int(r2 * i / 20)
        alpha = int(8 * (1 - i / 20))
        od.ellipse([cx2 - ri, cy2 - ri, cx2 + ri, cy2 + ri], fill=(*accent, alpha))

    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _draw_deco(img, w, h, theme):
    """绘制装饰元素"""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    accent = theme["accent"]
    random.seed(42)

    ox, oy = w - int(w * 0.22), h - int(h * 0.37)
    for row in range(5):
        for col in range(7):
            px, py = ox + col * 26, oy + row * 26
            if 0 <= px < w and 0 <= py < h:
                od.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(*accent, 25))

    for _ in range(6):
        x = random.randint(30, w - 30)
        y = random.randint(20, h - 20)
        r = random.randint(20, 55)
        od.ellipse([x - r, y - r, x + r, y + r], outline=(*accent, 20), width=1)

    for i in range(3):
        y = int(h * 0.19) + i * 12
        od.line([(30, y), (30 + 28 + i * 14, y)], fill=(*accent, 25), width=1)

    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


# ─── 宽封面（三级结构）────────────────────────────────────────────

def _generate_wide_cover(title, sub_series, series, theme):
    """生成 900x383 宽封面：系列名（左上角）+ 子分类（居中）+ 标题（卡片）"""
    img = Image.new("RGB", (WIDE_W, WIDE_H))
    _draw_bg(img, WIDE_W, WIDE_H, theme)
    _draw_glow(img, WIDE_W, WIDE_H, theme)
    _draw_deco(img, WIDE_W, WIDE_H, theme)

    draw = ImageDraw.Draw(img)

    # 标题字号与玻璃卡片
    fs = _title_font_size(title)
    font = _find_font(fs)
    bb = draw.textbbox((0, 0), title, font=font)
    tw = bb[2] - bb[0]

    card_w = min(max(tw + 160, 560), 780)
    max_w = card_w - 50
    lines = _wrap_text(draw, title, font, max_w)

    line_count = len(lines)
    card_h = 120 if line_count <= 1 else (120 + (line_count - 1) * 50)
    card_h = min(card_h, 200)

    cx = (WIDE_W - card_w) // 2
    cy = (WIDE_H - card_h) // 2 + 30

    # 玻璃卡片
    overlay = Image.new("RGBA", (WIDE_W, WIDE_H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=16,
                         fill=theme["card"], outline=theme["card_border"], width=1)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
    draw = ImageDraw.Draw(img)

    # 系列名（左上角）
    font_top = _find_font(26)
    top_color = theme["sub"]
    bb = draw.textbbox((0, 0), series, font=font_top)
    draw.text((30, 24 - bb[1]), series, font=font_top, fill=top_color)

    # 子分类（居中，accent 色 + 装饰线）
    if sub_series:
        font_sub = _find_font(30)
        sub_color = theme["accent"]
        bb = draw.textbbox((0, 0), sub_series, font=font_sub)
        sw = bb[2] - bb[0]
        sh = bb[3] - bb[1]
        sx = (WIDE_W - sw) // 2
        sy = cy - 58

        line_y = sy + sh // 2
        line_w = 36
        draw.line([(sx - line_w - 6, line_y), (sx - 6, line_y)], fill=theme["accent"], width=2)
        draw.line([(sx + sw + 6, line_y), (sx + sw + line_w + 6, line_y)], fill=theme["accent"], width=2)
        draw.text((sx, sy - bb[1]), sub_series, font=font_sub, fill=sub_color)

    # 标题（卡片内居中）
    bb_s = font.getbbox("测Ag")
    line_h = int((bb_s[3] - bb_s[1]) * 1.3)
    total_h = len(lines) * line_h
    start_y = cy + (card_h - total_h) // 2

    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font)
        lw = bb[2] - bb[0]
        lx = (WIDE_W - lw) // 2
        ly = start_y + i * line_h
        draw.text((lx + 1, ly + 1), line, font=font, fill=(0, 0, 0, 80))
        draw.text((lx, ly), line, font=font, fill=theme["text"])

    # 底部装饰条
    bar_w = 50
    bar_y = cy + card_h - 14
    bar_x = (WIDE_W - bar_w) // 2
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 2], radius=2, fill=theme["accent"])

    return img


# ─── 方封面（三级结构）────────────────────────────────────────────

def _generate_square_cover(title, sub_series, series, theme):
    """生成 900x900 方封面：大字体独立排版，适配小尺寸缩略图展示

    方封面在微信中展示尺寸很小（缩略图），因此：
    - 字体全部放大，保证小尺寸下可读
    - 减少装饰元素，把空间留给文字
    - 与横版封面完全不同的排版逻辑
    """
    S = SQUARE_SIZE
    img = Image.new("RGB", (S, S))
    _draw_bg(img, S, S, theme)
    _draw_glow(img, S, S, theme)
    _draw_deco(img, S, S, theme)

    draw = ImageDraw.Draw(img)

    # ── 字体定义 ──
    font_series = _find_font(48)
    font_sub = _find_font(64)
    title_fs = _title_font_size(title, base=100)
    font_t = _find_font(title_fs)

    # 计算各元素实际高度
    series_bb = draw.textbbox((0, 0), series, font=font_series)
    series_h = series_bb[3] - series_bb[1]
    series_w = series_bb[2] - series_bb[0]

    sub_bb = draw.textbbox((0, 0), sub_series, font=font_sub)
    sub_h = sub_bb[3] - sub_bb[1]
    sw = sub_bb[2] - sub_bb[0]
    sub_top = sub_bb[1]  # 基线以上的偏移（负值）

    max_w = S - 100
    title_lines = _wrap_text(draw, title, font_t, max_w)
    bb_s = font_t.getbbox("测Ag")
    line_h = int((bb_s[3] - bb_s[1]) * 1.25)
    title_total_h = len(title_lines) * line_h

    # 4 个等距空隙：上边距、系列名→子分类、子分类→标题、下边距
    total_content_h = series_h + sub_h + title_total_h
    gap = (S - total_content_h) // 4

    # ── 系列名（居中）──
    series_x = (S - series_w) // 2
    series_y = gap
    draw.text((series_x, series_y), series, font=font_series, fill=theme["sub"])

    # ── 子分类（居中，粗体大字 + 粗装饰线）──
    sx = (S - sw) // 2
    sy = series_y + series_h + gap

    # 装饰线对齐文字视觉中心（补偿 textbbox 的基线偏移）
    sub_line_y = sy + sub_top + sub_h // 2
    sub_line_w = 55
    draw.line([(sx - sub_line_w - 14, sub_line_y), (sx - 14, sub_line_y)], fill=theme["accent"], width=3)
    draw.line([(sx + sw + 14, sub_line_y), (sx + sw + sub_line_w + 14, sub_line_y)], fill=theme["accent"], width=3)
    draw.text((sx, sy), sub_series, font=font_sub, fill=theme["accent"])

    # ── 标题（居中大字，白字 + 粗阴影）──
    title_start_y = sy + sub_h + gap

    for i, line in enumerate(title_lines):
        bb = draw.textbbox((0, 0), line, font=font_t)
        lw = bb[2] - bb[0]
        lx = (S - lw) // 2
        ly = title_start_y + i * line_h
        draw.text((lx + 2, ly + 2), line, font=font_t, fill=(0, 0, 0, 100))
        draw.text((lx, ly), line, font=font_t, fill=theme["text"])

    # 粗装饰条（紧跟标题下方）
    bar_w = 60
    bar_y = title_start_y + title_total_h + 28
    bar_x = (S - bar_w) // 2
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 4], radius=2, fill=theme["accent"])

    return img


# ─── 拼接 ─────────────────────────────────────────────────────────

def get_crop_coords() -> tuple[str, str]:
    """返回拼接封面的裁剪坐标

    拼接图布局：宽封面（2.35:1）在上，方封面（1:1）在下。
    pic_crop_235_1 裁剪上半部分，pic_crop_1_1 裁剪下半部分。

    Returns:
        (pic_crop_235_1, pic_crop_1_1)
        格式: "X1_Y1_X2_Y2"（0~1 比例坐标）
    """
    y_split = round(WIDE_H / TOTAL_H, 4)  # 383 / 1283 ≈ 0.2985
    pic_crop_235_1 = f"0_0_1_{y_split}"
    pic_crop_1_1 = f"0_{y_split}_1_1"
    return pic_crop_235_1, pic_crop_1_1


def generate_cover_combined(
    title: str,
    sub_series: str = "",
    series: str = "AI Agent 学习+面试指南",
    output_path: str | Path | None = None,
    theme_name: str = "ocean",
) -> tuple[Path, str, str]:
    """生成拼接封面图（宽封面 + 方封面）

    Args:
        title: 文章标题
        sub_series: 子分类（如 "LLM 基础"）
        series: 系列名（如 "AI Agent 学习+面试指南"）
        output_path: 输出文件路径
        theme_name: 配色主题

    Returns:
        (output_path, pic_crop_235_1, pic_crop_1_1) 裁剪坐标用于 API 调用
    """
    theme = THEMES.get(theme_name, THEMES["ocean"])

    if output_path is None:
        output_path = Path("cover_combined.png")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成宽封面
    wide_img = _generate_wide_cover(title, sub_series, series, theme)

    # 生成方封面（三级结构：系列名 + 子分类 + 标题）
    square_img = _generate_square_cover(title, sub_series or title, series, theme)

    # 拼接（宽封面在上，方封面在下）
    combined = Image.new("RGB", (TOTAL_W, TOTAL_H))
    combined.paste(wide_img, (0, 0))
    combined.paste(square_img, (0, WIDE_H))

    combined.save(str(output_path), "PNG")

    # 计算裁剪坐标
    pic_crop_235_1, pic_crop_1_1 = get_crop_coords()

    print(f"[OK] 拼接封面已生成: {output_path}")
    print(f"     总尺寸: {TOTAL_W}x{TOTAL_H}  (宽封面 {WIDE_W}x{WIDE_H} + 方封面 {SQUARE_SIZE}x{SQUARE_SIZE})")
    print(f"     裁剪坐标: pic_crop_235_1={pic_crop_235_1}  pic_crop_1_1={pic_crop_1_1}")

    return output_path, pic_crop_235_1, pic_crop_1_1


# ─── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="生成微信拼接封面图（宽封面 + 方封面）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python generate_cover_combined.py "认识大语言模型" --sub "LLM 基础"
  python generate_cover_combined.py "Agent 循环" --sub "Agent 循环" --theme midnight --output cover.png
        """,
    )
    parser.add_argument("title", help="文章标题")
    parser.add_argument("--sub", default="", help="子分类（如 'LLM 基础'）")
    parser.add_argument("--series", default="AI Agent 学习+面试指南", help="系列名（默认 'AI Agent 学习+面试指南'）")
    parser.add_argument("--theme", default="ocean",
                        choices=["aurora", "ocean", "midnight", "sunset", "forest"],
                        help="配色主题（默认 ocean）")
    parser.add_argument("--output", default="cover_combined.png", help="输出路径（默认 cover_combined.png）")

    args = parser.parse_args()
    generate_cover_combined(
        title=args.title,
        sub_series=args.sub,
        series=args.series,
        output_path=args.output,
        theme_name=args.theme,
    )


if __name__ == "__main__":
    main()
