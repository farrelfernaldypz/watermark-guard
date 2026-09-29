import io
from pathlib import Path

import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

from watermark.dwt_dct_watermark import embed_watermark


def test_detect_page_extracts_owner_identity_from_uploaded_watermark():
    secret = "detection-test-key"
    owner_identity = "Detection Test Owner"
    pixels = np.random.default_rng(29).integers(
        0, 256, (512, 512, 3), dtype=np.uint8
    )
    watermarked, _ = embed_watermark(Image.fromarray(pixels), owner_identity, secret)
    image_buffer = io.BytesIO()
    watermarked.save(image_buffer, format="PNG")

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=20)
    app.session_state["active_page"] = "Detect Watermark"
    app.run()

    app.file_uploader(key="detect_image").set_value(
        ("watermarked.png", image_buffer.getvalue(), "image/png")
    ).run()
    app.text_input(key="detect_secret").set_value(secret).run()
    app.button[-1].click().run()

    assert not app.exception
    assert any(owner_identity in element.value for element in app.markdown), [
        element.value for element in app.markdown
    ]
    assert any("Watermark Detected" in element.value for element in app.markdown)
    assert all(button.label != "Recovery" for button in app.button)

    app.text_input(key="detect_secret").set_value("incorrect-key").run()
    app.button[-1].click().run()

    assert any("Watermark Not Detected" in element.value for element in app.markdown)
    assert any("Secret Key tidak valid" in element.value for element in app.caption)
