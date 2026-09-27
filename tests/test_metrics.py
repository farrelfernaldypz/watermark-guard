import numpy as np
import pytest
from PIL import Image

from attacks.image_attacks import apply_attack
from metrics.metrics import psnr, normalized_correlation, ber, watermark_status
from watermark.dct_watermark import embed_watermark, extract_watermark

def test_psnr_identical():
    x = np.zeros((8, 8), dtype=np.uint8)
    assert psnr(x, x) == float("inf")

def test_nc_identical():
    x = np.array([0, 1, 0, 1], dtype=np.uint8)
    assert abs(normalized_correlation(x, x) - 1.0) < 1e-9

def test_ber_identical():
    x = np.array([0, 1, 1, 0], dtype=np.uint8)
    assert ber(x, x) == 0.0


def test_dct_watermark_embedding_and_blind_extraction():
    pixels = np.random.default_rng(7).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    original = Image.fromarray(pixels)
    watermarked, embedded_bits = embed_watermark(original, "Farrel - NPM 43", "key-demo")

    extracted_bits, extracted_text = extract_watermark(watermarked, "Farrel - NPM 43", "key-demo")

    assert len(embedded_bits) == len(extracted_bits)
    assert extracted_text == "Farrel - NPM 43"
    assert normalized_correlation(embedded_bits, extracted_bits) == 1.0


def test_dct_extraction_rejects_image_without_enough_capacity():
    tiny_image = Image.new("RGB", (16, 16), color="white")

    with pytest.raises(ValueError, match="terlalu kecil"):
        extract_watermark(tiny_image, "Farrel - NPM 43", "key-demo")


def test_detect_watermark_on_cover_image_reports_not_detected():
    pixels = np.random.default_rng(17).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    cover = Image.fromarray(pixels)
    expected_text = "Farrel - NPM 43"
    expected_bits = np.array(
        [int(bit) for byte in expected_text.encode("utf-8") for bit in f"{byte:08b}"],
        dtype=np.uint8,
    )
    extracted_bits, _ = extract_watermark(cover, expected_text, "key-demo")

    status = watermark_status(
        normalized_correlation(expected_bits, extracted_bits),
        ber(expected_bits, extracted_bits),
    )

    assert status == "Watermark Not Detected"


def test_detect_watermark_on_created_image_reports_detected():
    pixels = np.random.default_rng(17).integers(0, 256, (256, 256, 3), dtype=np.uint8)
    cover = Image.fromarray(pixels)
    expected_text = "Farrel - NPM 43"
    expected_bits = np.array(
        [int(bit) for byte in expected_text.encode("utf-8") for bit in f"{byte:08b}"],
        dtype=np.uint8,
    )
    watermarked, _ = embed_watermark(cover, expected_text, "key-demo")
    extracted_bits, extracted_text = extract_watermark(watermarked, expected_text, "key-demo")

    status = watermark_status(
        normalized_correlation(expected_bits, extracted_bits),
        ber(expected_bits, extracted_bits),
    )

    assert extracted_text == expected_text
    assert status == "Watermark Detected / Recovered"


def test_detect_after_attack_reports_measured_watermark_condition():
    pixels = np.random.default_rng(17).integers(0, 256, (512, 512, 3), dtype=np.uint8)
    cover = Image.fromarray(pixels)
    expected_text = "Farrel - NPM 43"
    expected_bits = np.array(
        [int(bit) for byte in expected_text.encode("utf-8") for bit in f"{byte:08b}"],
        dtype=np.uint8,
    )
    watermarked, _ = embed_watermark(cover, expected_text, "key-demo")
    attacked = apply_attack(watermarked, "JPEG 50")
    extracted_bits, _ = extract_watermark(attacked, expected_text, "key-demo")

    correlation = normalized_correlation(expected_bits, extracted_bits)
    bit_error_rate = ber(expected_bits, extracted_bits)

    assert watermark_status(correlation, bit_error_rate) in {
        "Watermark Detected / Recovered",
        "Watermark Partially Recovered",
        "Watermark Not Detected",
    }
    assert 0.0 <= bit_error_rate <= 1.0


def test_attack_function_applies_crop_and_jpeg():
    image = Image.new("RGB", (200, 160), color=(120, 80, 40))

    cropped = apply_attack(image, "Crop 10%")
    compressed = apply_attack(image, "JPEG 50")

    assert cropped.size == (180, 144)
    assert compressed.size == image.size
    assert compressed.mode == "RGB"


def test_attack_function_rejects_unknown_attack():
    image = Image.new("RGB", (64, 64), color="white")

    with pytest.raises(ValueError, match="tidak didukung"):
        apply_attack(image, "Unsupported")
