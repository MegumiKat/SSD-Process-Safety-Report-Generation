#!/usr/bin/env python
"""
make_logo_transparent.py

把带白色/浅色背景的 JPG/PNG Logo 转成透明背景 PNG。

用法示例：
    python make_logo_transparent.py input_logo.jpg output_logo.png
    python make_logo_transparent.py logo.jpg logo.png --bg-color 255 255 255 --tolerance 15
"""

import argparse
from pathlib import Path

from PIL import Image


def make_background_transparent(
    input_path: Path,
    output_path: Path,
    bg_color=(0, 0, 0),
    tolerance: int = 10,
) -> None:
    """
    将接近 bg_color 的像素变成透明（alpha=0），其他像素保持不变。

    :param input_path: 输入图片路径（JPG/PNG 都可以）
    :param output_path: 输出 PNG 路径
    :param bg_color: 背景颜色 (R, G, B)，默认白色
    :param tolerance: 容差（0-255），越大说明“离 bg_color 有点差距也算背景”
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    r_bg, g_bg, b_bg = bg_color
    new_data = []

    for item in datas:
        r, g, b, a = item

        # 计算与背景色的“距离”（简单绝对差方式）
        if (
            abs(r - r_bg) <= tolerance
            and abs(g - g_bg) <= tolerance
            and abs(b - b_bg) <= tolerance
        ):
            # 视作背景：设为完全透明
            new_data.append((r_bg, g_bg, b_bg, 0))
        else:
            # 其他区域保留原来的像素（含原本的 alpha）
            new_data.append((r, g, b, a))

    img.putdata(new_data)

    # 确保是 png 后缀
    if output_path.suffix.lower() != ".png":
        output_path = output_path.with_suffix(".png")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    print(f"Saved transparent logo to: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert logo image background to transparent PNG."
    )
    parser.add_argument("input", type=str, help="Input image path (jpg/png)")
    parser.add_argument("output", type=str, help="Output image path (png)")
    parser.add_argument(
        "--bg-color",
        nargs=3,
        type=int,
        metavar=("R", "G", "B"),
        default=[0, 0, 0],
        help="Background color to treat as transparent (default: 255 255 255)",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=10,
        help="Tolerance for background match 0-255 (default: 10)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    bg_color = tuple(args.bg_color)
    tolerance = args.tolerance

    make_background_transparent(
        input_path=input_path,
        output_path=output_path,
        bg_color=bg_color,
        tolerance=tolerance,
    )


if __name__ == "__main__":
    main()