import hashlib
import numpy as np
import cv2
from PIL import Image

# Mid-frequency coefficient pair in an 8x8 DCT block.
P1 = (3, 4)
P2 = (4, 3)

def _key_seed(secret: str) -> int:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)

def _text_bits(text: str) -> np.ndarray:
    raw = text.encode("utf-8")
    bits = []
    for byte in raw:
        bits.extend(int(x) for x in f"{byte:08b}")
    return np.array(bits, dtype=np.uint8)

def _prepare_gray(image: Image.Image):
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape
    h8, w8 = h - h % 8, w - w % 8
    return rgb, gray, h8, w8

def _block_positions(h8, w8, seed):
    positions = [(y, x) for y in range(0, h8, 8) for x in range(0, w8, 8)]
    rng = np.random.default_rng(seed)
    rng.shuffle(positions)
    return positions

def embed_watermark(image: Image.Image, text: str, secret: str, strength: float = 18.0):
    rgb, gray, h8, w8 = _prepare_gray(image)
    bits = _text_bits(text)
    positions = _block_positions(h8, w8, _key_seed(secret))
    if len(bits) > len(positions):
        raise ValueError("Gambar terlalu kecil untuk watermark ini.")

    work = gray.copy()
    for bit, (y, x) in zip(bits, positions):
        block = work[y:y+8, x:x+8] - 128.0
        d = cv2.dct(block)
        a = d[P1]
        b = d[P2]
        if bit == 1:
            target = max(a, b, 1.0)
            d[P1], d[P2] = target + strength/2, target - strength/2
        else:
            target = max(a, b, 1.0)
            d[P1], d[P2] = target - strength/2, target + strength/2
        work[y:y+8, x:x+8] = cv2.idct(d) + 128.0

    out_gray = np.clip(work, 0, 255).astype(np.uint8)
    out = rgb.copy()
    # Preserve color appearance while modifying luminance.
    yuv = cv2.cvtColor(out, cv2.COLOR_RGB2YUV)
    yuv[..., 0] = out_gray
    out = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)
    return Image.fromarray(out), bits

def extract_watermark(image: Image.Image, expected_text: str, secret: str):
    if not secret:
        raise ValueError("Secret key wajib diisi.")
    if not expected_text:
        raise ValueError("Expected watermark text wajib diisi.")
    _, gray, h8, w8 = _prepare_gray(image)
    expected_bits = _text_bits(expected_text)
    positions = _block_positions(h8, w8, _key_seed(secret))
    if len(expected_bits) > len(positions):
        raise ValueError(
            "Gambar terlalu kecil untuk mengekstrak seluruh watermark. "
            "Gunakan gambar dengan resolusi lebih besar atau watermark lebih pendek."
        )

    bits = []
    for y, x in positions[:len(expected_bits)]:
        block = gray[y:y+8, x:x+8] - 128.0
        d = cv2.dct(block)
        bits.append(1 if d[P1] > d[P2] else 0)

    bits = np.array(bits, dtype=np.uint8)
    raw = bytearray()
    for i in range(0, len(bits) - 7, 8):
        byte = int("".join(map(str, bits[i:i+8])), 2)
        raw.append(byte)
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    return bits, text
