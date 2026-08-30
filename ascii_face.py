# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "opencv-python-headless<5.0.0",
#     "pillow>=10.0.0",
#     "numpy>=1.24.0",
# ]
# ///
"""
ascii_face.py - 高精度人脸与五官（眼/鼻/嘴/发型/轮廓）ASCII 字符画生成器

使用示例:
    # 1. 高反差素描线条模式 (五官极其清晰锐利, 默认输出到终端并保存到 ascii_out.txt)
    uv run ascii_face.py "微信图片_20260605222854_71960_665.jpg" --width 80 --ramp crisp

    # 2. 超细腻 70 阶灰度模式
    uv run ascii_face.py "微信图片_20260605222854_71960_665.jpg" --width 80 --ramp detailed

    # 3. ANSI 24-bit TrueColor 真彩色终端渲染
    uv run ascii_face.py "微信图片_20260605222854_71960_665.jpg" --width 80 --color

    # 4. 白底黑字文档导出模式 (用于浅色编辑器/Markdown查看)
    uv run ascii_face.py "微信图片_20260605222854_71960_665.jpg" --width 80 --mode light -o face_light.txt
"""

import sys
import argparse
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

# 确保 Windows 控制台与终端统一使用 UTF-8 编码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 常用字符密度映射表 (从暗到亮 / 密度递减)
RAMPS = {
    # 35阶高反差素描字符表 (眼睛、鼻子、嘴巴、发丝线条极强)
    "crisp": r"""$#W&8@Q0OZmwqpdbkhao*+~<>i!;:,"^`'. """[::-1],
    # 70阶超细腻灰度字符表 (丰富明暗层次过渡)
    "detailed": r"""$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,"^`'. """[::-1],
    # 经典 10阶 jp2a 字符表
    "classic": r"""@%#*+=-:. """,
    # Unicode 方块灰度字符
    "blocks": " ░▒▓█",
}


def load_image_unicode(path: str) -> np.ndarray:
    """
    安全读取图像，全面兼容 Windows 下包含中文或特殊字符的路径。
    返回 RGB 格式的 numpy 数组 (H, W, 3)。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"未找到指定图像文件: {path}")
    pil_img = Image.open(str(p)).convert("RGB")
    return np.array(pil_img)


def detect_and_crop_face(
    img_rgb: np.ndarray,
    pad_top: float = 0.45,
    pad_bottom: float = 1.45,
    pad_sides: float = 0.40,
):
    """
    智能检测人脸与关键区域，按黄金比例扩边裁剪以完整保留发型顶部、面部五官及领口/西装比例。
    """
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    H, W = gray.shape

    # 优先使用对正面人脸精度极高的 alt2 模型，备选 default 模型
    cascades = [
        cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"),
        cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"),
    ]

    faces = []
    for cascade in cascades:
        detected = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60)
        )
        if len(detected) > 0:
            faces = detected
            break

    if len(faces) == 0:
        # Fallback: 若未检测到人脸，按常规人像居中比例裁剪
        top, bottom = 0, int(H * 0.75)
        left, right = int(W * 0.1), int(W * 0.9)
        return img_rgb[top:bottom, left:right], (0, 0, W, H), []

    # 选取最居中且面积适宜的人脸
    best_face = max(faces, key=lambda f: f[2] * f[3] - 0.2 * abs((f[0] + f[2] / 2) - W / 2) ** 2)
    fx, fy, fw, fh = best_face

    # 尝试在面部定位双眼
    roi_gray = gray[fy : fy + int(fh * 0.7), fx : fx + fw]
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=3, minSize=(25, 25))

    # 根据比例扩充包围盒
    top = max(0, int(fy - fh * pad_top))
    bottom = min(H, int(fy + fh * pad_bottom))
    left = max(0, int(fx - fw * pad_sides))
    right = min(W, int(fx + fw * (1.0 + pad_sides)))

    cropped_rgb = img_rgb[top:bottom, left:right]
    face_bbox = (fx - left, fy - top, fw, fh)
    eye_bboxes = [(ex + fx - left, ey + fy - top, ew, eh) for (ex, ey, ew, eh) in eyes]

    return cropped_rgb, face_bbox, eye_bboxes


def enhance_facial_details(
    img_rgb: np.ndarray,
    face_bbox=None,
    eye_bboxes=None,
    contrast_clip: float = 3.5,
    feature_boost: float = 3.0,
    edge_strength: float = 1.5,
    clean_skin: bool = True,
    brow_soft: float = 0.0,
) -> np.ndarray:
    """
    解剖级五官微结构定位与高保真线条融合增强引擎:
    1. 双边滤波保边去噪，净化平滑肤色背景
    2. 多尺度差分高斯 (DoG) + 自适应梯度阈值提取眼睛、瞳孔轮廓、睫毛、鼻孔、唇线微结构
    3. 五官核心区域 (黑眼珠/眼神光、剑眉毛流、山根鼻梁、鼻翼鼻孔、M型唇峰、唇中缝闭合线) 局部靶向强化
    4. 彻底强化眼睛、眼珠、鼻型与嘴型轮廓，素描立体感极强
    """
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    cH, cW = gray.shape

    if face_bbox is not None:
        r_fx, r_fy, fw, fh = face_bbox
    else:
        r_fx, r_fy, fw, fh = int(cW * 0.2), int(cH * 0.2), int(cW * 0.6), int(cH * 0.6)

    # 1. 双边滤波: 平滑面部微弱噪点，保留五官锐利边缘
    bilateral = cv2.bilateralFilter(gray, d=7, sigmaColor=30, sigmaSpace=30)

    # 2. 多尺度高频微结构提取 (DoG + Adaptive Threshold + Morphological Gradient)
    g1 = cv2.GaussianBlur(gray, (0, 0), sigmaX=0.5)
    g2 = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.0)
    dog = g1.astype(np.float32) - g2.astype(np.float32)
    dog_lines = np.clip(-dog * 4.0, 0, 255)

    adapt_lines = cv2.adaptiveThreshold(
        bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 9, 3
    ).astype(np.float32)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    morph_grad = cv2.morphologyEx(bilateral, cv2.MORPH_GRADIENT, kernel).astype(np.float32)
    morph_grad = np.clip(morph_grad * 2.2, 0, 255)

    # 综合边缘特征 (包含瞳孔边缘、眼线、鼻翼、唇线)
    edge_map = np.maximum(dog_lines * 0.8, adapt_lines * 0.5) + morph_grad * 0.4
    edge_map = np.clip(edge_map, 0, 255)

    # 3. 构建五官核心敏感区靶向权重掩膜
    feature_weight_mask = np.ones((cH, cW), dtype=np.float32) * 0.8
    # 面部整体
    cv2.ellipse(
        feature_weight_mask,
        (r_fx + fw // 2, r_fy + int(fh * 0.55)),
        (int(fw * 0.48), int(fh * 0.56)),
        0, 0, 360, 1.2, -1,
    )
    # 眉毛与眼部重点区 (Top 18%~48%) — brow_soft 只降此带权重, 眼珠靠下方瞳孔圆保持强度
    brow_zone_weight = max(1.0, 3.0 - brow_soft)
    cv2.rectangle(
        feature_weight_mask,
        (r_fx + int(fw * 0.10), r_fy + int(fh * 0.18)),
        (r_fx + int(fw * 0.90), r_fy + int(fh * 0.48)),
        brow_zone_weight, -1,
    )
    # 双眼眼珠与瞳孔靶向聚焦加权
    if eye_bboxes and len(eye_bboxes) > 0:
        for (ex, ey, ew, eh) in eye_bboxes:
            cv2.circle(feature_weight_mask, (ex + ew // 2, ey + eh // 2), int(ew * 0.6), 3.8, -1)

    # 鼻梁与鼻孔重点区 (46%~68%)
    cv2.rectangle(
        feature_weight_mask,
        (r_fx + int(fw * 0.28), r_fy + int(fh * 0.46)),
        (r_fx + int(fw * 0.72), r_fy + int(fh * 0.68)),
        2.6, -1,
    )
    # 鼻翼与鼻孔焦点加强
    cv2.ellipse(
        feature_weight_mask,
        (r_fx + fw // 2, r_fy + int(fh * 0.59)),
        (int(fw * 0.18), int(fh * 0.08)),
        0, 0, 360, 3.2, -1,
    )
    # 唇部、M唇峰与唇中缝闭合线重点区 (67%~88%)
    cv2.rectangle(
        feature_weight_mask,
        (r_fx + int(fw * 0.22), r_fy + int(fh * 0.67)),
        (r_fx + int(fw * 0.78), r_fy + int(fh * 0.88)),
        3.0, -1,
    )
    feature_weight_mask = cv2.GaussianBlur(feature_weight_mask, (15, 15), 0)

    # 4. CLAHE 局部自适应直方图均衡化 (提取基础光影层次)
    clahe = cv2.createCLAHE(clipLimit=contrast_clip, tileGridSize=(8, 8))
    base_tonal = clahe.apply(bilateral).astype(np.float32)

    # 5. 特征线条增益与底模非线性融合
    boosted_lines = (edge_map / 255.0) * feature_weight_mask * (feature_boost * 0.45 * edge_strength)
    boosted_lines = np.clip(boosted_lines, 0, 1.0)

    norm_tonal = base_tonal / 255.0
    dark_component = (1.0 - norm_tonal)
    combined_dark = np.clip(dark_component + boosted_lines * 0.85, 0, 1.0)

    # 6. 肤色净化: 抑制非线条区域的漫反射中灰杂色，使五官如同素描般在干净面庞上跃然纸上
    if clean_skin:
        skin_mask = (norm_tonal > 0.45) & (boosted_lines < 0.22)
        combined_dark[skin_mask] = combined_dark[skin_mask] * 0.55

    # 转换为 0~255 输出 (0=深色线条/瞳孔/眉毛/发丝/西装, 255=明亮肤色/背景)
    final_brightness = (1.0 - combined_dark) * 255.0
    final_brightness = np.clip(final_brightness, 0, 255).astype(np.uint8)

    return final_brightness


def render_ascii(
    enhanced_gray: np.ndarray,
    orig_rgb: np.ndarray,
    width: int,
    ramp_name: str = "crisp",
    invert: bool = False,
    color: bool = False,
    aspect_ratio: float = 0.52,
) -> str:
    """
    将图像渲染为高保真 ASCII 字符画字符串。
    - invert=False: 适配深色终端 (黑底)，亮像素对应较密字符，暗像素对应稀疏点
    - invert=True: 适配浅色背景/文本文档 (白底)，暗像素对应稠密字符
    - color=True: 生成 ANSI 24-bit TrueColor 彩色字符
    """
    H, W = enhanced_gray.shape
    out_h = max(1, int((H / W) * width * aspect_ratio))

    resized_gray = cv2.resize(
        enhanced_gray, (width, out_h), interpolation=cv2.INTER_AREA
    ).astype(np.float32)

    if color:
        resized_rgb = cv2.resize(orig_rgb, (width, out_h), interpolation=cv2.INTER_AREA)

    ramp = RAMPS.get(ramp_name, RAMPS["crisp"])
    if invert:
        ramp = ramp[::-1]

    n_chars = len(ramp)
    lines = []

    for r in range(out_h):
        row_chars = []
        for c in range(width):
            val = resized_gray[r, c]
            idx = min(n_chars - 1, max(0, int(val * (n_chars - 1) / 255.0)))
            ch = ramp[idx]

            if color:
                cr, cg, cb = resized_rgb[r, c]
                row_chars.append(f"\033[38;2;{cr};{cg};{cb}m{ch}\033[0m")
            else:
                row_chars.append(ch)
        lines.append("".join(row_chars))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="高精度人脸与五官（眼/鼻/嘴/发型/轮廓）ASCII 字符画生成器 (支持 uv 一键运行与 TrueColor 彩色终端)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", help="输入图片路径 (支持中文与任意路径)")
    parser.add_argument(
        "-w", "--width", type=int, default=80, help="输出 ASCII 字符宽度 (列数, 默认: 80)"
    )
    parser.add_argument(
        "-m",
        "--mode",
        choices=["dark", "light"],
        default="dark",
        help="终端显示主题: dark(深色终端默认), light(浅色背景/文本阅读)",
    )
    parser.add_argument(
        "-r",
        "--ramp",
        choices=list(RAMPS.keys()),
        default="crisp",
        help="字符密度表: crisp(高反差素描推荐), detailed(70阶超细), classic(10阶), blocks(方块)",
    )
    parser.add_argument(
        "-c", "--color", action="store_true", help="开启 ANSI 24-bit TrueColor 真彩色终端输出"
    )
    parser.add_argument(
        "--no-crop", action="store_true", help="不进行人脸自动裁剪，转换整张原始图片"
    )
    parser.add_argument(
        "-F", "--feature-boost", type=float, default=3.0, help="五官特征（眼鼻嘴眉）增强权重 (默认: 3.0)"
    )
    parser.add_argument(
        "-C", "--contrast", type=float, default=3.5, help="CLAHE 对比度增强系数 (默认: 3.5)"
    )
    parser.add_argument(
        "-e", "--edge", type=float, default=1.5, help="边缘与结构线条锐化强度 (默认: 1.5)"
    )
    parser.add_argument(
        "--brow-soft", type=float, default=0.0, help="眉毛柔和度 (越大眉毛越轻越温和, 0=默认锐利)"
    )
    parser.add_argument(
        "-o", "--output", default="ascii_out.txt", help="纯文本字符画保存路径 (默认: ascii_out.txt)"
    )

    args = parser.parse_args()

    # 1. 安全加载图像
    img_rgb = load_image_unicode(args.image)

    # 2. 人脸检测与智能构图裁剪
    if not args.no_crop:
        processed_rgb, face_bbox, eye_bboxes = detect_and_crop_face(img_rgb)
    else:
        processed_rgb = img_rgb
        face_bbox, eye_bboxes = None, []

    # 3. 语义级五官细节与微结构增强
    enhanced_gray = enhance_facial_details(
        processed_rgb,
        face_bbox=face_bbox,
        eye_bboxes=eye_bboxes,
        contrast_clip=args.contrast,
        feature_boost=args.feature_boost,
        edge_strength=args.edge,
        brow_soft=args.brow_soft,
    )

    # 4. 渲染用于终端输出的 ASCII (支持彩色或深/浅色模式)
    invert_terminal = (args.mode == "light")
    terminal_art = render_ascii(
        enhanced_gray,
        processed_rgb,
        width=args.width,
        ramp_name=args.ramp,
        invert=invert_terminal,
        color=args.color,
    )

    # 5. 渲染用于文本文件保存的 ASCII (文件在浅色背景/常规编辑器中查看，默认反转映射更清晰)
    file_art = render_ascii(
        enhanced_gray,
        processed_rgb,
        width=args.width,
        ramp_name=args.ramp,
        invert=True,  # 白底黑字
        color=False,
    )

    # 输出到终端
    print(terminal_art)

    # 保存至文件
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(file_art, encoding="utf-8")
        print(f"\n[OK] ASCII 字符画已成功保存至: {out_path.resolve()}", file=sys.stderr)


if __name__ == "__main__":
    main()