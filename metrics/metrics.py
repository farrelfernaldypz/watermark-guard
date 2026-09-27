import numpy as np

def psnr(original, processed):
    a = np.asarray(original).astype(np.float64)
    b = np.asarray(processed).astype(np.float64)
    if a.shape != b.shape:
        raise ValueError("Ukuran gambar harus sama untuk PSNR.")
    mse = np.mean((a - b) ** 2)
    if mse == 0:
        return float("inf")
    return 10 * np.log10((255.0 ** 2) / mse)

def normalized_correlation(a, b):
    a = np.asarray(a).astype(np.float64).flatten()
    b = np.asarray(b).astype(np.float64).flatten()
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    a, b = a[:n], b[:n]
    a = 2*a - 1
    b = 2*b - 1
    den = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / den) if den else 0.0

def ber(expected, actual):
    expected = np.asarray(expected).astype(np.uint8).flatten()
    actual = np.asarray(actual).astype(np.uint8).flatten()
    n = min(len(expected), len(actual))
    if n == 0:
        return 1.0
    return float(np.mean(expected[:n] != actual[:n]))


def watermark_status(correlation, bit_error_rate):
    # Prototype thresholds; validate these cutoffs against measured experiment results.
    if correlation >= 0.80 and bit_error_rate <= 0.20:
        return "Watermark Detected / Recovered"
    if correlation >= 0.50 and bit_error_rate <= 0.50:
        return "Watermark Partially Recovered"
    return "Watermark Not Detected"
