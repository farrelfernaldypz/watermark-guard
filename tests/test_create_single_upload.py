import io
from pathlib import Path

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest
from watermark.secret_key_registry import SecretKeyRegistry
from watermark.dwt_dct_watermark import extract_watermark_by_key


def make_upload(name: str, seed: int) -> tuple[str, bytes, str]:
    pixels = np.random.default_rng(seed).integers(
        0, 256, (512, 512, 3), dtype=np.uint8
    )
    buffer = io.BytesIO()
    Image.fromarray(pixels).save(buffer, format="PNG")
    return name, buffer.getvalue(), "image/png"


def test_create_single_upload_replaces_previous_image_and_processes_one():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=30)
    app.session_state["active_page"] = "Create Watermark"
    app.run()

    app.file_uploader(key="create_image").set_value(
        make_upload("first.png", 1)
    ).run()
    assert app.session_state["create_image"].name == "first.png"

    app.file_uploader(key="create_image").set_value(
        make_upload("replacement.png", 2)
    ).run()
    assert app.session_state["create_image"].name == "replacement.png"
    assert "create_images" not in app.session_state

    app.text_input(key="watermark_text").set_value("Single Owner").run()
    app.button(key="create_watermark").click().run()

    results = app.session_state["created_watermark_results"]
    assert len(results) == 1
    assert results[0]["name"] == "replacement.png"
    assert results[0]["error"] is None
    assert app.session_state["created_secret_key"]
    watermark_id = app.session_state["created_watermark_id"]
    first_secret_key = app.session_state["created_secret_key"]
    registry = SecretKeyRegistry.from_environment()
    assert registry.get_secret_key(watermark_id) == first_secret_key
    watermarked_image = Image.open(io.BytesIO(results[0]["watermarked_bytes"])).convert("RGB")
    extracted, observed_tag, expected_tag = extract_watermark_by_key(
        watermarked_image,
        registry.get_secret_key(watermark_id),
    )
    assert extracted == "Single Owner"
    assert np.array_equal(observed_tag, expected_tag)

    app.run()
    app.text_input(key="watermark_recovery_id").set_value(watermark_id).run()
    app.button(key="retrieve_secret_key").click().run()
    assert app.session_state["recovered_secret_key"] == first_secret_key
    assert not app.exception
