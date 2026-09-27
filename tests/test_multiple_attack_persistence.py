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
        ("watermarked.png", uploaded_image, "image/png")
    ).run()
    app.multiselect[0].set_value(["JPEG 90", "Resize 75%"]).run()
    app.button[-1].click().run()

    first_results = app.session_state["multiple_attack_results"]
    assert [result["attack_name"] for result in first_results] == ["JPEG 90", "Resize 75%"]
    assert applied_attacks == ["JPEG 90", "Resize 75%"]
    saved_image_bytes = [result["image_bytes"] for result in first_results]
    assert len(app.get("download_button")) == 2

    app.run()

    rerun_results = app.session_state["multiple_attack_results"]
    assert [result["image_bytes"] for result in rerun_results] == saved_image_bytes
    assert len(app.get("download_button")) == 2
    assert applied_attacks == ["JPEG 90", "Resize 75%"]
    assert not app.exception
