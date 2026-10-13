"""한글 글리프 페이지 생성 (512x512, 4비트 인덱스, PSMT4HH 로 업로드).

원본 폰트 팔레트(CLUT 16색)를 그대로 쓴다:
 0 투명, 4 흰색 채움, 5 밝은 회색(164), 3 어두운 회색(88) — 채움 가장자리,
 2 검은 외곽선, 1 반투명 검정(43), 6 옅은 검정(21) — 외곽선 바깥 가장자리.
원본처럼 2px 검은 외곽선 + 이탤릭(기울임) 처리.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PITCH = 21          # 셀 간격(px)
CELL = 20           # 셀 내용 크기(px)
COLS = 512 // PITCH  # 24
SS = 4              # 슈퍼샘플링 배율
FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NanumSquareNeo-dEb.ttf')
SIZE = 15.5         # 채움 글자 크기(px, 1배 기준)
SHEAR = 0.21        # 이탤릭 기울기 (원본과 비슷하게)
OUTLINE = 1.9       # 외곽선 두께(px)


def cell_xy(i, y0=0):
    return (i % COLS) * PITCH, y0 + (i // COLS) * PITCH


def render_glyph(ch, font):
    n = CELL * SS
    img = Image.new('L', (n * 2, n * 2), 0)
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), ch, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    ox = n - w / 2 - bb[0]
    oy = n - h / 2 - bb[1]
    d.text((ox, oy), ch, font=font, fill=255)
    # 기울임: 위쪽이 오른쪽으로 (x' = x + (cy - y) * SHEAR)
    img = img.transform(img.size, Image.AFFINE, (1, SHEAR, -SHEAR * n, 0, 1, 0), resample=Image.BICUBIC)
    # 셀 크기로 자르기 (중앙)
    c = n // 2
    img = img.crop((c, c, c + n, c + n))
    fill = np.asarray(img, np.float32) / 255
    # 외곽선: 원형 팽창
    r = int(round(OUTLINE * SS))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (xx * xx + yy * yy) <= r * r + r
    pad = np.pad(fill > 0.5, r)
    out = np.zeros_like(fill, bool)
    for dy, dx in zip(*np.nonzero(disk)):
        out |= pad[dy:dy + n, dx:dx + n]
    # 다운샘플 (평균)
    f = fill.reshape(CELL, SS, CELL, SS).mean((1, 3))
    o = out.astype(np.float32).reshape(CELL, SS, CELL, SS).mean((1, 3))
    idx = np.zeros((CELL, CELL), np.uint8)
    idx[o >= 0.12] = 6
    idx[o >= 0.35] = 1
    idx[o >= 0.6] = 2
    idx[f >= 0.2] = 3
    idx[f >= 0.45] = 5
    idx[f >= 0.75] = 4
    return idx


def build_page(chars, y0=0):
    font = ImageFont.truetype(FONT, int(round(SIZE * SS)))
    page = np.zeros((512, 512), np.uint8)
    assert len(chars) <= COLS * ((512 - y0) // PITCH), len(chars)
    for i, ch in enumerate(chars):
        x, y = cell_xy(i, y0)
        page[y:y + CELL, x:x + CELL] = render_glyph(ch, font)
    return page


def pack4(page):
    """4비트 선형(하위 니블 = 짝수 픽셀)"""
    p = page.astype(np.uint8)
    return (p[:, 0::2] | (p[:, 1::2] << 4)).tobytes()


PAL = {0: (0, 0, 0, 0), 1: (0, 0, 0, 170), 2: (0, 0, 0, 255), 3: (88, 88, 88, 255), 4: (255, 255, 255, 255),
       5: (164, 164, 164, 255), 6: (0, 0, 0, 85)}


def preview(page):
    rgba = np.zeros(page.shape + (4,), np.uint8)
    for k, v in PAL.items():
        rgba[page == k] = v
    return Image.fromarray(rgba, 'RGBA')
