import hashlib
import hmac

import cv2
import numpy as np
from PIL import Image


# The level-1 Haar LL band retains image structure and survives compression,
# resampling, and mild noise better than the high-frequency detail bands.
# DCT mid-frequency coefficient differences in LL balance visibility and durability.
_BLOCK_SIZE = 8
_COEFFICIENT_A = (1, 2)
_COEFFICIENT_B = (2, 1)
_QIM_STEP = 140.0
_REPETITIONS = 3
_FRAME_MAGIC = b"WGD2"
_LENGTH_SIZE = 2
_TAG_SIZE = 16
_HEADER_SIZE = len(_FRAME_MAGIC) + _LENGTH_SIZE


def _key_seed(secret: str) -> int:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def _text_bits(text: str) -> np.ndarray:
    return _bytes_bits(text.encode("utf-8"))


def _bytes_bits(raw: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(raw, dtype=np.uint8))


def _bits_bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits).tobytes()


def _haar_dwt(
    gray: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, tuple[int, int]]:
    """Return one-level orthonormal Haar LL, LH, HL, HH bands and source size."""
    height, width = gray.shape
    padded_height = height + height % 2
    padded_width = width + width % 2
    padded = np.pad(
        gray,
        ((0, padded_height - height), (0, padded_width - width)),
        mode="edge",
    )
    a = padded[0::2, 0::2]
    b = padded[0::2, 1::2]
    c = padded[1::2, 0::2]
    d = padded[1::2, 1::2]

    ll = (a + b + c + d) * 0.5
    lh = (a - b + c - d) * 0.5
    hl = (a + b - c - d) * 0.5
    hh = (a - b - c + d) * 0.5
    return ll, lh, hl, hh, (height, width)


def _haar_idwt(
    ll: np.ndarray,
    lh: np.ndarray,
    hl: np.ndarray,
    hh: np.ndarray,
    source_size: tuple[int, int],
) -> np.ndarray:
    """Reconstruct a grayscale image from one-level orthonormal Haar bands."""
    reconstructed = np.empty((ll.shape[0] * 2, ll.shape[1] * 2), dtype=np.float32)
    reconstructed[0::2, 0::2] = (ll + lh + hl + hh) * 0.5
    reconstructed[0::2, 1::2] = (ll - lh + hl - hh) * 0.5
    reconstructed[1::2, 0::2] = (ll + lh - hl - hh) * 0.5
    reconstructed[1::2, 1::2] = (ll - lh - hl + hh) * 0.5
    return reconstructed[:source_size[0], :source_size[1]]


def _keyed_block_positions(height: int, width: int, secret: str) -> list[tuple[int, int]]:
    block_rows = height // _BLOCK_SIZE
    block_columns = width // _BLOCK_SIZE
    positions = [
        (row * _BLOCK_SIZE, column * _BLOCK_SIZE)
        for row in range(block_rows)
        for column in range(block_columns)
    ]
    np.random.default_rng(_key_seed(secret)).shuffle(positions)
    return positions


def _qim_embed_block(block: np.ndarray, bit: int) -> np.ndarray:
    coefficients = cv2.dct(block.astype(np.float32))
    difference = float(coefficients[_COEFFICIENT_A] - coefficients[_COEFFICIENT_B])
    lattice = int(np.rint((difference - bit * _QIM_STEP) / (2 * _QIM_STEP)))
    target = 2 * lattice * _QIM_STEP + bit * _QIM_STEP
    adjustment = (target - difference) * 0.5
    coefficients[_COEFFICIENT_A] += adjustment
    coefficients[_COEFFICIENT_B] -= adjustment
    return cv2.idct(coefficients)


def _qim_read_block(block: np.ndarray) -> int:
    coefficients = cv2.dct(block.astype(np.float32))
    difference = float(coefficients[_COEFFICIENT_A] - coefficients[_COEFFICIENT_B])
    return int(np.rint(difference / _QIM_STEP)) & 1


def _read_majority_bits(
    ll: np.ndarray, positions: list[tuple[int, int]], bit_count: int
) -> np.ndarray:
    encoded_count = bit_count * _REPETITIONS
    encoded = np.empty(min(encoded_count, len(positions)), dtype=np.uint8)
    for index, (y, x) in enumerate(positions[:encoded_count]):
        block = ll[y:y + _BLOCK_SIZE, x:x + _BLOCK_SIZE]
        encoded[index] = _qim_read_block(block)
    if len(encoded) != encoded_count:
        return np.array([], dtype=np.uint8)
    return (encoded.reshape(bit_count, _REPETITIONS).sum(axis=1) >= 2).astype(np.uint8)


def _encode_frame(text: str, secret: str) -> tuple[bytes, bytes]:
    payload = text.encode("utf-8")
    if len(payload) > (2**(8 * _LENGTH_SIZE) - 1):
        raise ValueError("Teks watermark terlalu panjang.")
    header = _FRAME_MAGIC + len(payload).to_bytes(_LENGTH_SIZE, "big")
    tag = hmac.new(
        secret.encode("utf-8"), header + payload, hashlib.sha256
    ).digest()[:_TAG_SIZE]
    return header + payload + tag, payload


def _decode_candidate(
    majority_bits: np.ndarray, secret: str
) -> tuple[str | None, np.ndarray | None, np.ndarray | None]:
    if len(majority_bits) < _HEADER_SIZE * 8:
        return None, None, None
    header = _bits_bytes(majority_bits[:_HEADER_SIZE * 8])
    if header[:len(_FRAME_MAGIC)] != _FRAME_MAGIC:
        return None, None, None

    payload_length = int.from_bytes(header[len(_FRAME_MAGIC):], "big")
    tag_start = _HEADER_SIZE * 8 + payload_length * 8
    frame_end = tag_start + _TAG_SIZE * 8
    if frame_end > len(majority_bits):
        return None, None, None

    payload_bits = majority_bits[_HEADER_SIZE * 8:tag_start]
    observed_tag_bits = majority_bits[tag_start:frame_end]
    payload = _bits_bytes(payload_bits)
    expected_tag = hmac.new(
        secret.encode("utf-8"), header + payload, hashlib.sha256
    ).digest()[:_TAG_SIZE]
    expected_tag_bits = _bytes_bits(expected_tag)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return text, observed_tag_bits, expected_tag_bits


def _prepare_image(
    image: Image.Image,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[int, int],
]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    ll, lh, hl, hh, source_size = _haar_dwt(gray)
    return rgb, ll, lh, hl, hh, source_size


def embed_watermark(
    image: Image.Image, text: str, secret: str
) -> tuple[Image.Image, np.ndarray]:
    """Embed UTF-8 text in Haar-LL DCT mid-frequency coefficient pairs."""
    if not secret:
        raise ValueError("Secret key wajib diisi.")

    rgb, ll, lh, hl, hh, source_size = _prepare_image(image)
    frame, payload = _encode_frame(text, secret)
    frame_bits = _bytes_bits(frame)
    repeated_bits = np.repeat(frame_bits, _REPETITIONS)
    positions = _keyed_block_positions(ll.shape[0], ll.shape[1], secret)
    if len(repeated_bits) > len(positions):
        raise ValueError("Gambar terlalu kecil untuk watermark ini.")

    for bit, (y, x) in zip(repeated_bits, positions):
        ll[y:y + _BLOCK_SIZE, x:x + _BLOCK_SIZE] = _qim_embed_block(
            ll[y:y + _BLOCK_SIZE, x:x + _BLOCK_SIZE], int(bit)
        )

    gray = _haar_idwt(ll, lh, hl, hh, source_size)
    yuv = cv2.cvtColor(rgb, cv2.COLOR_RGB2YUV)
    yuv[..., 0] = np.clip(gray, 0, 255).astype(np.uint8)
    output = cv2.cvtColor(yuv, cv2.COLOR_YUV2RGB)
    return Image.fromarray(output), _text_bits(payload.decode("utf-8"))


def extract_watermark_by_key(
    image: Image.Image, secret: str
) -> tuple[str | None, np.ndarray | None, np.ndarray | None]:
    """Blindly extract UTF-8 text and return observed/expected HMAC tag bits."""
    if not secret:
        raise ValueError("Secret key wajib diisi.")

    _, ll, _, _, _, _ = _prepare_image(image)
    positions = _keyed_block_positions(ll.shape[0], ll.shape[1], secret)
    header_capacity = _HEADER_SIZE * 8
    header_bits = _read_majority_bits(ll, positions, header_capacity)
    if len(header_bits) != header_capacity:
        return None, None, None
    header = _bits_bytes(header_bits)
    if header[:len(_FRAME_MAGIC)] != _FRAME_MAGIC:
        return None, None, None

    payload_length = int.from_bytes(header[len(_FRAME_MAGIC):], "big")
    frame_bits = (_HEADER_SIZE + payload_length + _TAG_SIZE) * 8
    majority_bits = _read_majority_bits(ll, positions, frame_bits)
    if len(majority_bits) != frame_bits:
        return None, None, None
    return _decode_candidate(majority_bits, secret)
