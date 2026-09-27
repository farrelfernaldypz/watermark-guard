import numpy as np
import pytest
from PIL import Image

from attacks.image_attacks import apply_attack
from metrics.metrics import ber, normalized_correlation, psnr, watermark_status
from watermark.dwt_dct_watermark import embed_watermark, extract_watermark_by_key


def make_cover(seed: int = 17) -> Image.Image:
    pixels = np.random.default_rng(seed).integers(0, 256, (512, 512, 3), dtype=np.uint8)
    return Image.fromarray(pixels)


def assert_watermark_extracts(image: Image.Image, text: str, secret: str) -> None:
    extracted_text, observed_tag, expected_tag = extract_watermark_by_key(image, secret)

    assert extracted_text == text
    assert observed_tag is not None
    assert expected_tag is not None
    assert np.array_equal(observed_tag, expected_tag)

    correlation = normalized_correlation(expected_tag, observed_tag)
    bit_error_rate = ber(expected_tag, observed_tag)
    assert abs(correlation - 1.0) < 1e-12
    assert bit_error_rate == 0.0
    assert watermark_status(correlation, bit_error_rate) == "Watermark Detected"


def test_psnr_identical():
    x = np.zeros((8, 8), dtype=np.uint8)
    assert psnr(x, x) == float("inf")


def test_nc_identical():
    x = np.array([0, 1, 0, 1], dtype=np.uint8)
    assert abs(normalized_correlation(x, x) - 1.0) < 1e-9


def test_ber_identical():
    x = np.array([0, 1, 1, 0], dtype=np.uint8)
    assert ber(x, x) == 0.0


def test_hybrid_dwt_dct_round_trip_and_psnr():
    text = "Owner Example 42"
    cover = make_cover()
    watermarked, _ = embed_watermark(cover, text, "key-demo")

    assert_watermark_extracts(watermarked, text, "key-demo")
    assert psnr(np.asarray(cover), np.asarray(watermarked)) > 30


def test_hybrid_extraction_rejects_wrong_secret():
    watermarked, _ = embed_watermark(make_cover(), "Owner Example 42", "correct-key")

    extracted_text, observed_tag, expected_tag = extract_watermark_by_key(
        watermarked, "incorrect-key"
    )

    assert extracted_text is None
    assert observed_tag is None
    assert expected_tag is None


@pytest.mark.parametrize(
    "attack",
    ["JPEG 90", "Resize 75%", "Gaussian Noise", "Gaussian Blur"],
)
def test_hybrid_watermark_extracts_after_targeted_attacks(attack: str):
    text = "Owner Example 42"
    watermarked, _ = embed_watermark(make_cover(), text, "key-demo")
    attacked = apply_attack(watermarked, attack)

    assert_watermark_extracts(attacked, text, "key-demo")


def test_hybrid_embedding_rejects_image_without_capacity():
    tiny_image = Image.new("RGB", (16, 16), color="white")

    with pytest.raises(ValueError, match="terlalu kecil"):
        embed_watermark(tiny_image, "Owner Example", "key-demo")


def test_attack_function_applies_crop_jpeg_and_blur():
    image = Image.new("RGB", (200, 160), color=(120, 80, 40))

    cropped = apply_attack(image, "Crop 10%")
    compressed = apply_attack(image, "JPEG 50")
    blurred = apply_attack(image, "Gaussian Blur")

    assert cropped.size == (180, 144)
    assert compressed.size == image.size
    assert compressed.mode == "RGB"
    assert blurred.size == image.size


def test_attack_function_rejects_unknown_attack():
    image = Image.new("RGB", (64, 64), color="white")

    with pytest.raises(ValueError, match="tidak didukung"):
        apply_attack(image, "Unsupported")
