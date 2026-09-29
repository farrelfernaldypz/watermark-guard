import io
from pathlib import Path

from PIL import Image
from streamlit.testing.v1 import AppTest

from attacks import image_attacks


def test_multiple_attack_results_remain_after_rerun(monkeypatch):
    applied_attacks = []
    original_apply_attack = image_attacks.apply_attack

    def track_attack(image, attack_name):
        applied_attacks.append(attack_name)
        return original_apply_attack(image, attack_name)

    monkeypatch.setattr(image_attacks, "apply_attack", track_attack)

    buffer = io.BytesIO()
    Image.new("RGB", (512, 512), color="white").save(buffer, format="PNG")
    uploaded_image = buffer.getvalue()

    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=20)
    app.session_state["active_page"] = "Attack"
    app.session_state["attack_mode"] = "Multiple Attacks"
    app.run()

    app.file_uploader(key="attack_image").set_value(
        ("foto_pemandangan.png", uploaded_image, "image/png")
    ).run()
    selected_attacks = [
        "JPEG 90",
        "JPEG 70",
        "JPEG 50",
        "Crop 10%",
        "Resize 75%",
        "Gaussian Noise",
        "Gaussian Blur",
        "Brightness +20",
        "Contrast 1.2",
    ]
    app.multiselect[0].set_value(selected_attacks).run()
    app.button[-1].click().run()

    first_results = app.session_state["multiple_attack_results"]
    assert [result["attack_name"] for result in first_results] == selected_attacks
    assert [result["file_name"] for result in first_results] == [
        "attacked_jpeg_90_foto_pemandangan.jpg",
        "attacked_jpeg_70_foto_pemandangan.jpg",
        "attacked_jpeg_50_foto_pemandangan.jpg",
        "attacked_crop_10pct_foto_pemandangan.png",
        "attacked_resize_75pct_foto_pemandangan.png",
        "attacked_gaussian_noise_foto_pemandangan.png",
        "attacked_gaussian_blur_foto_pemandangan.png",
        "attacked_brightness_plus20_foto_pemandangan.png",
        "attacked_contrast_1.2_foto_pemandangan.png",
    ]
    assert applied_attacks == selected_attacks
    saved_image_bytes = [result["image_bytes"] for result in first_results]
    assert len(app.get("download_button")) == len(selected_attacks)

    app.run()

    rerun_results = app.session_state["multiple_attack_results"]
    assert [result["image_bytes"] for result in rerun_results] == saved_image_bytes
    assert len(app.get("download_button")) == len(selected_attacks)
    assert applied_attacks == selected_attacks
    assert not app.exception
