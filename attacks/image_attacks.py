import io
import numpy as np
import cv2
from PIL import Image, ImageEnhance

def apply_attack(image: Image.Image, attack: str) -> Image.Image:
    if not isinstance(image, Image.Image):
        raise ValueError("Attack input harus berupa gambar yang valid.")

    if attack in {"JPEG 90", "JPEG 70", "JPEG 50"}:
        quality = int(attack.split()[1])
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        buf.seek(0)
        return Image.open(buf).convert("RGB")

    arr = np.asarray(image.convert("RGB"))

    if attack == "Crop 10%":
        h, w = arr.shape[:2]
        margin_y, margin_x = int(h * 0.05), int(w * 0.05)
        cropped = arr[margin_y:h-margin_y, margin_x:w-margin_x]
        if cropped.shape[0] < 1 or cropped.shape[1] < 1:
            raise ValueError("Gambar terlalu kecil untuk serangan Crop 10%.")
        return Image.fromarray(cropped)

    if attack == "Resize 75%":
        h, w = arr.shape[:2]
        small = cv2.resize(arr, (max(8, int(w*.75)), max(8, int(h*.75))),
                           interpolation=cv2.INTER_AREA)
        back = cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
        return Image.fromarray(back)

    if attack == "Gaussian Noise":
        rng = np.random.default_rng(12345)
        noise = rng.normal(0, 5, arr.shape)
        noisy = np.clip(arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy)

    if attack == "Brightness +20":
        return ImageEnhance.Brightness(image).enhance(1.20)

    if attack == "Contrast 1.2":
        return ImageEnhance.Contrast(image).enhance(1.20)

    raise ValueError(f"Jenis serangan tidak didukung: {attack}")
