import io

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError

from attacks.image_attacks import apply_attack
from metrics.metrics import ber, normalized_correlation, psnr, watermark_status
from watermark.dct_watermark import _text_bits, embed_watermark, extract_watermark


ATTACKS = [
    "JPEG 90",
    "JPEG 70",
    "JPEG 50",
    "Crop 10%",
    "Resize 75%",
    "Gaussian Noise",
    "Brightness +20",
    "Contrast 1.2",
]


def load_image(uploaded_file) -> Image.Image:
    """Decode an uploaded supported image and return an independent RGB image."""
    try:
        image = Image.open(uploaded_file)
        image.load()
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("File tidak dapat dibaca sebagai gambar PNG atau JPEG yang valid.") from error


def get_recovery_metrics(image: Image.Image, expected_text: str, secret: str):
    """Blindly extract a payload and compare it with the user's expected text."""
    bits, extracted_text = extract_watermark(image, expected_text, secret)
    expected_bits = _text_bits(expected_text)
    correlation = normalized_correlation(expected_bits, bits)
    bit_error_rate = ber(expected_bits, bits)
    return extracted_text, correlation, bit_error_rate


def image_bytes(image: Image.Image, image_format: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def navigate_to(page: str) -> None:
    st.session_state["active_page"] = page
    if page in {"Attack", "Recovery"}:
        st.session_state["attack_recovery_section"] = page


def navigate_to_selected_testing_page() -> None:
    navigate_to(st.session_state["attack_recovery_section"])


def render_status(kind: str, message: str) -> None:
    st.markdown(
        f'<div class="wg-status wg-status-{kind}"><span>{message}</span></div>',
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="WatermarkGuard", layout="wide")
st.session_state.setdefault("active_page", "Create Watermark")
st.session_state.setdefault("attack_mode", "Single Attack")

# --- UI/UX CSS UPDATE KEDUA (AURORA GLASSMORPHISM) DITERAPKAN DI SINI ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        /* Warna Dasar & Glassmorphism */
        --color-glass-bg: rgba(30, 41, 59, 0.45);
        --color-glass-border: rgba(255, 255, 255, 0.1);
        --color-glass-hover: rgba(255, 255, 255, 0.05);
        
        /* Tipografi */
        --color-text-main: #f8fafc;
        --color-text-muted: #94a3b8;
        
        /* Aksen Gradasi Modern (Biru - Ungu - Pink) */
        --color-primary-grad: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #d946ef 100%);
        --color-primary-grad-hover: linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #c026d3 100%);
        
        /* Status Warna Pastel Neon */
        --color-success-bg: rgba(16, 185, 129, 0.15);
        --color-success-border: #10b981;
        --color-warning-bg: rgba(245, 158, 11, 0.15);
        --color-warning-border: #f59e0b;
        --color-danger-bg: rgba(239, 68, 68, 0.15);
        --color-danger-border: #ef4444;
    }

    /* Background Aplikasi: Mesh Gradient yang halus dan tidak bertabrakan */
    html, body, #root, [data-testid="stApp"],
    [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stMainBlockContainer"], .block-container,
    [data-testid="stHeader"] {
        background-color: #0b0f19 !important;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.12) 0%, transparent 40%),
            radial-gradient(circle at 90% 10%, rgba(217, 70, 239, 0.1) 0%, transparent 40%),
            radial-gradient(circle at 70% 80%, rgba(14, 165, 233, 0.1) 0%, transparent 45%),
            radial-gradient(circle at 20% 90%, rgba(16, 185, 129, 0.08) 0%, transparent 40%) !important;
        background-attachment: fixed !important;
        color: var(--color-text-main);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    [data-testid="stHeader"] { display: none; }
    [data-testid="stMainBlockContainer"], .block-container {
        width: 100%;
        max-width: none;
        padding: 0;
        margin: 0;
        box-sizing: border-box;
        overflow: visible;
    }
    .block-container > [data-testid="stVerticalBlock"] { gap: 0; }

    /* Modern Glass Navbar */
    .st-key-top_navbar {
        position: relative;
        display: block;
        width: 100%;
        min-height: 72px;
        box-sizing: border-box;
        margin: 0 0 2rem;
        padding: 0.5rem 2rem;
        overflow: visible;
        background: rgba(11, 15, 25, 0.6) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border-bottom: 1px solid var(--color-glass-border) !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2) !important;
    }
    .st-key-top_navbar > [data-testid="stVerticalBlock"] {
        width: 100%;
        min-height: 62px;
        justify-content: center;
        gap: 0;
    }
    .st-key-top_navbar [data-testid="stHorizontalBlock"] {
        width: 100%;
        min-height: 62px;
        align-items: center;
        flex-wrap: nowrap;
        gap: 1rem;
    }
    .st-key-top_navbar [data-testid="column"] {
        min-width: 0;
        display: flex;
        align-items: center;
    }
    .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(5) {
        display: none;
    }
    
    /* Brand Logo dengan Teks Bergradasi */
    .wg-brand {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        min-height: 2.5rem;
    }
    .wg-mark {
        display: grid;
        width: 2.3rem;
        height: 2.3rem;
        flex: 0 0 2.3rem;
        place-items: center;
        border-radius: 10px;
        background: var(--color-primary-grad);
        color: #ffffff;
        font-weight: 800;
        font-size: 0.9rem;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
    }
    .wg-brand-name {
        background: var(--color-primary-grad);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.25rem;
        font-weight: 800;
        white-space: nowrap;
        letter-spacing: -0.02em;
    }

    /* Popover & Menu Dropdowns */
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
        background: rgba(15, 23, 42, 0.9) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--color-glass-border) !important;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5) !important;
    }
    [data-baseweb="popover"] [data-testid="stCaptionContainer"] { display: none; }
    
    /* Main Content Container */
    .st-key-wg_content {
        width: 100%;
        max-width: 960px;
        box-sizing: border-box;
        margin: 0 auto;
        padding: 0 2rem 3rem;
    }
    .st-key-wg_content > [data-testid="stVerticalBlock"] { gap: 1.5rem; }
    
    /* Global Text Styles Override for Dark Mode */
    h1, h2, h3, h4, h5, h6, [data-testid="stWidgetLabel"] p, label, .stMarkdown p {
        color: var(--color-text-main) !important;
    }
    p, small, [data-testid="stCaptionContainer"], .stMarkdown small { 
        color: var(--color-text-muted) !important; 
    }
    
    .wg-page-header { margin: 0 0 1rem; }
    .wg-page-header h1 {
        margin: 0;
        font-size: clamp(1.8rem, 2.8vw, 2.5rem);
        line-height: 1.25;
        font-weight: 800;
        letter-spacing: -0.03em;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .wg-page-header p { margin: 0.5rem 0 0; font-size: 1rem; font-weight: 400;}
    .wg-section-heading {
        margin: 0 0 0.8rem;
        color: var(--color-text-main);
        font-size: 1.1rem;
        line-height: 1.35;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        opacity: 0.9;
    }

    /* Container Cards - Efek Kaca Buram */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--color-glass-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--color-glass-border);
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        padding: 1.5rem !important;
        transition: border-color 0.3s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(255, 255, 255, 0.2);
    }

    /* File Uploader */
    [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"] {
        background-color: transparent;
    }
    [data-testid="stFileUploaderDropzone"] {
        min-height: 8rem;
        background: rgba(15, 23, 42, 0.4) !important;
        border: 2px dashed rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #a855f7 !important;
        background: rgba(168, 85, 247, 0.05) !important;
    }
    [data-testid="stFileUploaderDropzone"] svg { color: #a855f7; fill: #a855f7; }
    [data-testid="stFileUploaderDropzone"] button {
        border: 1px solid var(--color-glass-border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.05);
        color: var(--color-text-main);
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: var(--color-primary-grad);
        border-color: transparent;
        color: #fff;
    }

    /* Text Inputs, TextAreas, Selectboxes */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        min-height: 2.75rem;
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px;
        color: var(--color-text-main) !important;
        transition: all 0.25s ease;
    }
    [data-testid="stTextInput"] input::placeholder { color: var(--color-text-muted); }
    [data-testid="stTextInput"] button { border: none; background-color: transparent; }
    [data-testid="stTextInput"] button svg { color: var(--color-text-muted); fill: var(--color-text-muted); }
    
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
        border-color: #a855f7 !important;
        box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.2) !important;
        outline: none;
    }

    input[type="radio"], input[type="checkbox"] { accent-color: #a855f7; }
    
    /* Buttons Primary (TOMBOL GRADASI KEREN) */
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] button {
        min-height: 2.75rem;
        background: var(--color-primary-grad) !important;
        border: none !important;
        border-radius: 10px;
        color: #ffffff !important;
        font-weight: 700;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stDownloadButton"] button:hover {
        background: var(--color-primary-grad-hover) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5) !important;
    }
    
    /* Buttons Secondary */
    [data-testid="stButton"] button[kind="secondary"] {
        min-height: 2.75rem;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid var(--color-glass-border) !important;
        border-radius: 10px;
        color: var(--color-text-main) !important;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    [data-testid="stButton"] button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    [data-testid="stButton"] button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none !important;
    }

    /* Metrics Box */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--color-glass-border);
        border-left: 4px solid #a855f7;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    [data-testid="stMetric"] label { color: var(--color-text-muted) !important; font-size: 0.9rem; font-weight: 600; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--color-text-main) !important; font-weight: 800; }

    /* Progress & Spinner */
    [data-testid="stProgressBar"] div { background: var(--color-primary-grad); }
    [data-testid="stSpinner"] svg { color: #a855f7; }

    /* Tables dengan Tema Transparan */
    [data-testid="stTable"] { overflow-x: auto; border-radius: 12px; border: 1px solid var(--color-glass-border); }
    [data-testid="stTable"] table { border-collapse: collapse; background: rgba(15, 23, 42, 0.4); width: 100%; }
    [data-testid="stTable"] th {
        background: rgba(255, 255, 255, 0.05);
        color: var(--color-text-main);
        border-bottom: 1px solid var(--color-glass-border);
        font-weight: 700;
        padding: 1rem;
    }
    [data-testid="stTable"] td {
        background: transparent;
        color: var(--color-text-muted);
        border-bottom: 1px solid var(--color-glass-border);
        padding: 0.8rem 1rem;
    }

    /* Result Status - Neon Alerts */
    .wg-result-status {
        margin-top: 1rem;
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        backdrop-filter: blur(8px);
        letter-spacing: 0.5px;
    }
    .wg-result-detected { background: var(--color-success-bg); color: #34d399; border: 1px solid var(--color-success-border); box-shadow: 0 0 15px rgba(16, 185, 129, 0.2); }
    .wg-result-partial { background: var(--color-warning-bg); color: #fbbf24; border: 1px solid var(--color-warning-border); box-shadow: 0 0 15px rgba(245, 158, 11, 0.2); }
    .wg-result-missing { background: var(--color-danger-bg); color: #f87171; border: 1px solid var(--color-danger-border); box-shadow: 0 0 15px rgba(239, 68, 68, 0.2); }

    /* Footer */
    .wg-footer {
        margin-top: 4rem;
        padding-top: 1.5rem;
        border-top: 1px solid var(--color-glass-border);
        color: var(--color-text-muted);
        font-size: 0.9rem;
        text-align: center;
        font-weight: 500;
    }
    
    a { color: #a855f7; text-decoration: none; transition: color 0.2s; }
    a:hover { color: #d946ef; }
    *:focus-visible { outline: 2px solid #a855f7; }

    /* Navbar Override Buttons Specificities */
    .st-key-top_navbar [data-testid="stButton"] > button,
    .st-key-top_navbar [data-testid="stPopover"] button {
        width: 100% !important;
        min-height: 2.6rem !important;
        padding: 0.45rem 1rem !important;
        border: 1px solid transparent !important;
        border-radius: 10px !important;
        background: transparent !important;
        background-color: transparent !important;
        color: var(--color-text-muted) !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        white-space: nowrap !important;
        box-shadow: none !important;
        transition: all 0.3s ease !important;
    }
    .st-key-top_navbar [data-testid="stButton"] > button:hover,
    .st-key-top_navbar [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
    }
    /* Aktif State di Navbar */
    .st-key-top_navbar [data-testid="stButton"] > button[kind="primary"],
    .st-key-top_navbar [data-testid="stPopover"] button[kind="primary"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        box-shadow: inset 0 0 15px rgba(255, 255, 255, 0.05) !important;
    }
    .st-key-top_navbar [data-testid="stButton"] p,
    .st-key-top_navbar [data-testid="stButton"] span,
    .st-key-top_navbar [data-testid="stPopover"] p,
    .st-key-top_navbar [data-testid="stPopover"] span {
        color: inherit !important;
    }
    .st-key-top_navbar [data-testid="stButton"] svg,
    .st-key-top_navbar [data-testid="stPopover"] svg {
        color: inherit !important;
        fill: currentColor !important;
    }

    /* Mobile Responsive adjustments */
    @media (max-width: 900px) {
        .st-key-top_navbar {
            padding: 0.5rem 1.25rem;
            margin-bottom: 1.5rem;
        }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] { gap: 0.5rem; }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"] { min-width: 0; }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3),
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
            display: none;
        }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) {
            flex: 1 1 auto;
        }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(5) {
            display: flex;
            flex: 0 0 3.5rem;
        }
        .st-key-wg_content { padding: 0 1.25rem 2rem; }
        .wg-page-header { margin-bottom: 0.5rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
# --- AKHIR DARI UPDATE CSS KEDUA ---

active_page = st.session_state["active_page"]
parent_active = active_page in {"Attack", "Recovery"}

with st.container(key="top_navbar"):
    brand_column, create_column, detect_column, attack_column, mobile_column = st.columns(
        [2.7, 1.45, 1.45, 1.75, 0.55],
        vertical_alignment="center",
    )

    with brand_column:
        st.markdown(
            '<div class="wg-brand"><div class="wg-mark">WG</div>'
            '<span class="wg-brand-name">WatermarkGuard</span></div>',
            unsafe_allow_html=True,
        )

    with create_column:
        st.button(
            "Create Watermark",
            type="primary" if active_page == "Create Watermark" else "secondary",
            use_container_width=True,
            key="nav_create",
            on_click=navigate_to,
            args=("Create Watermark",),
        )

    with detect_column:
        st.button(
            "Detect Watermark",
            type="primary" if active_page == "Detect Watermark" else "secondary",
            use_container_width=True,
            key="nav_detect",
            on_click=navigate_to,
            args=("Detect Watermark",),
        )

    with attack_column:
        with st.popover(
            "Attack & Recovery  ▾",
            type="primary" if parent_active else "secondary",
            use_container_width=True,
            key="nav_attack_recovery",
        ):
            st.button(
                "Attack",
                type="primary" if active_page == "Attack" else "secondary",
                use_container_width=True,
                key="nav_attack",
                on_click=navigate_to,
                args=("Attack",),
            )
            st.button(
                "Recovery",
                type="primary" if active_page == "Recovery" else "secondary",
                use_container_width=True,
                key="nav_recovery",
                on_click=navigate_to,
                args=("Recovery",),
            )

    with mobile_column:
        with st.popover("☰", use_container_width=True, key="mobile_menu"):
            st.button(
                "Create Watermark",
                type="primary" if active_page == "Create Watermark" else "secondary",
                use_container_width=True,
                key="mobile_nav_create",
                on_click=navigate_to,
                args=("Create Watermark",),
            )
            st.button(
                "Detect Watermark",
                type="primary" if active_page == "Detect Watermark" else "secondary",
                use_container_width=True,
                key="mobile_nav_detect",
                on_click=navigate_to,
                args=("Detect Watermark",),
            )
            st.button(
                "Attack",
                type="primary" if active_page == "Attack" else "secondary",
                use_container_width=True,
                key="mobile_nav_attack",
                on_click=navigate_to,
                args=("Attack",),
            )
            st.button(
                "Recovery",
                type="primary" if active_page == "Recovery" else "secondary",
                use_container_width=True,
                key="mobile_nav_recovery",
                on_click=navigate_to,
                args=("Recovery",),
            )


def page_header(title: str, description: str) -> None:
    st.markdown(
        f'<header class="wg-page-header"><h1>{title}</h1><p>{description}</p></header>',
        unsafe_allow_html=True,
    )


def show_status(kind: str, message: str) -> None:
    st.markdown(
        f'<div class="wg-result-status wg-result-{kind}">{message}</div>',
        unsafe_allow_html=True,
    )


def show_error(message: str) -> None:
    st.error(message)


with st.container(key="wg_content"):
    if active_page == "Create Watermark":
        page_header("Create Watermark", "Embed an invisible watermark into your image.")

        with st.container(border=True):
            st.markdown('<div class="wg-section-heading">1. Cover image</div>', unsafe_allow_html=True)
            st.caption("Choose the image that will carry the watermark.")
            create_upload = st.file_uploader(
                "Upload Cover Image", type=["png", "jpg", "jpeg"], key="create_image"
            )
            if create_upload:
                try:
                    cover_preview = load_image(create_upload)
                    st.image(cover_preview, caption=f"{create_upload.name}", use_container_width=True)
                except ValueError as error:
                    show_error(str(error))

        with st.container(border=True):
            st.markdown('<div class="wg-section-heading">2. Watermark information</div>', unsafe_allow_html=True)
            watermark_text = st.text_input("Watermark text / owner identity", "Farrel - NPM 43")
            secret = st.text_input("Secret key", type="password", key="create_secret")
            st.caption("The text is embedded invisibly using keyed DCT mid-frequency positions.")

        create_clicked = st.button(
            "Create Watermark",
            type="primary",
            disabled=create_upload is None,
            use_container_width=True,
        )
        if create_clicked:
            if not secret.strip():
                show_error("Secret key wajib diisi.")
            elif not watermark_text:
                show_error("Teks watermark wajib diisi.")
            else:
                try:
                    with st.spinner("Creating watermark..."):
                        original = load_image(create_upload)
                        watermarked, _ = embed_watermark(original, watermark_text, secret)
                        quality = psnr(np.asarray(original), np.asarray(watermarked))
                    st.markdown("### Result")
                    with st.container(border=True):
                        left, right = st.columns(2)
                        left.image(original, caption="Original Image", use_container_width=True)
                        right.image(watermarked, caption="Watermarked Image", use_container_width=True)
                        metric_column, info_column = st.columns([1, 2])
                        metric_column.metric("PSNR", f"{quality:.2f} dB")
                        info_column.markdown(f"**Watermark created**  \n{watermark_text}")
                        show_status("detected", "✓ Watermark Created")
                        with st.expander("View watermark effect"):
                            original_array = np.asarray(original).astype(np.int16)
                            watermarked_array = np.asarray(watermarked).astype(np.int16)
                            difference = np.max(np.abs(original_array - watermarked_array), axis=2)
                            difference_map = np.clip(difference * 8, 0, 255).astype(np.uint8)
                            st.image(
                                difference_map,
                                caption="Difference map · changes amplified for visualization",
                                clamp=True,
                                use_container_width=True,
                            )
                        st.download_button(
                            "Download Watermarked Image",
                            image_bytes(watermarked, "PNG"),
                            file_name="watermarked.png",
                            mime="image/png",
                        )
                except (ValueError, OSError, UnidentifiedImageError) as error:
                    show_error(str(error))

    elif active_page == "Detect Watermark":
        page_header("Detect Watermark", "Verify whether an image contains a valid watermark.")

        with st.container(border=True):
            st.markdown('<div class="wg-section-heading">Image and verification details</div>', unsafe_allow_html=True)
            detect_upload = st.file_uploader(
                "Upload Image", type=["png", "jpg", "jpeg"], key="detect_image"
            )
            if detect_upload:
                try:
                    detect_preview = load_image(detect_upload)
                    st.image(detect_preview, caption=detect_upload.name, use_container_width=True)
                except ValueError as error:
                    show_error(str(error))
            detect_secret = st.text_input("Secret key", type="password", key="detect_secret")
            detect_expected = st.text_input(
                "Expected watermark text", "Farrel - NPM 43", key="detect_expected"
            )
            st.caption("The original cover image is not required. Expected text is used to compare extracted bits.")
            detect_clicked = st.button(
                "Detect Watermark",
                type="primary",
                disabled=detect_upload is None,
                use_container_width=True,
            )

        if detect_clicked:
            if not detect_secret.strip():
                show_error("Secret key wajib diisi.")
            elif not detect_expected:
                show_error("Expected watermark text wajib diisi untuk verifikasi.")
            else:
                try:
                    with st.spinner("Checking watermark..."):
                        image = load_image(detect_upload)
                        extracted, correlation, bit_error_rate = get_recovery_metrics(
                            image, detect_expected, detect_secret
                        )
                        status = watermark_status(correlation, bit_error_rate)
                    st.markdown("### Detection Result")
                    with st.container(border=True):
                        if status == "Watermark Detected / Recovered":
                            show_status("detected", "✓ Watermark Detected")
                        elif status == "Watermark Partially Recovered":
                            show_status("partial", "! Watermark Partially Detected · possibly altered")
                        else:
                            show_status("missing", "× Watermark Not Detected")
                        st.image(image, caption="Image checked", use_container_width=True)
                        first, second = st.columns(2)
                        first.metric("NC · bit similarity", f"{correlation:.4f}")
                        second.metric("BER · bit errors", f"{bit_error_rate:.4f}")
                        st.markdown(f"**Expected watermark**  \n{detect_expected}")
                        st.markdown(f"**Extracted preview**  \n{extracted or '(text unreadable)'}")
                except (ValueError, OSError, UnidentifiedImageError) as error:
                    show_error(str(error))

    else:
        testing_page = active_page
        page_header("Attack & Recovery", "Test and recover your watermark after image manipulation.")

        testing_page = st.radio(
            "Attack & Recovery",
            ["Attack", "Recovery"],
            horizontal=True,
            key="attack_recovery_section",
            label_visibility="collapsed",
            on_change=navigate_to_selected_testing_page,
        )
        if testing_page == "Attack":
                st.markdown('<div class="wg-section-heading">Attack</div>', unsafe_allow_html=True)
                st.caption("Test the robustness of your watermark against common image attacks.")
                with st.container(border=True):
                    st.markdown('<div class="wg-section-heading">1. Watermarked image</div>', unsafe_allow_html=True)
                    attack_upload = st.file_uploader(
                        "Upload Watermarked Image", type=["png", "jpg", "jpeg"], key="attack_image"
                    )
                    if attack_upload:
                        try:
                            attack_preview = load_image(attack_upload)
                            st.image(attack_preview, caption=attack_upload.name, use_container_width=True)
                        except ValueError as error:
                            show_error(str(error))

                with st.container(border=True):
                    st.markdown('<div class="wg-section-heading">2. Attack settings</div>', unsafe_allow_html=True)
                    mode = st.radio(
                        "Attack mode", ["Single Attack", "Multiple Attacks"], horizontal=True, key="attack_mode"
                    )
                    if mode == "Single Attack":
                        selected_attacks = [st.selectbox("Attack type", ATTACKS)]
                    else:
                        selected_attacks = st.multiselect("Attack types", ATTACKS, default=ATTACKS)
                    attack_secret = st.text_input(
                        "Secret key · for NC / BER evaluation", type="password", key="attack_secret"
                    )
                    attack_expected = st.text_input(
                        "Expected watermark text",
                        "Farrel - NPM 43",
                        key="attack_expected",
                    )
                    attack_clicked = st.button(
                        "Apply Attack",
                        type="primary",
                        disabled=attack_upload is None,
                        use_container_width=True,
                    )

                if attack_clicked:
                    if not selected_attacks:
                        show_error("Pilih minimal satu jenis serangan.")
                    elif not attack_secret.strip() or not attack_expected:
                        show_error("Secret key dan expected watermark text dibutuhkan untuk menghitung NC / BER.")
                    else:
                        try:
                            watermarked = load_image(attack_upload)
                            result_rows = []
                            with st.spinner("Applying attack and measuring watermark..."):
                                for index, attack_name in enumerate(selected_attacks, start=1):
                                    attacked = apply_attack(watermarked, attack_name)
                                    output_format = "JPEG" if attack_name.startswith("JPEG") else "PNG"
                                    extension = "jpg" if output_format == "JPEG" else "png"
                                    try:
                                        extracted, correlation, bit_error_rate = get_recovery_metrics(
                                            attacked, attack_expected, attack_secret
                                        )
                                        status = watermark_status(correlation, bit_error_rate)
                                    except ValueError as error:
                                        extracted = "Tidak dapat diekstrak: gambar terlalu kecil"
                                        correlation, bit_error_rate = 0.0, 1.0
                                        status = "Watermark Not Detected"
                                        st.warning(f"{attack_name}: {error}")

                                    attack_psnr = (
                                        f"{psnr(np.asarray(watermarked), np.asarray(attacked)):.2f} dB"
                                        if watermarked.size == attacked.size
                                        else "N/A (dimensi berubah)"
                                    )
                                    result_rows.append(
                                        {
                                            "Attack": attack_name.split()[0],
                                            "Parameter": " ".join(attack_name.split()[1:]) or attack_name,
                                            "PSNR vs Watermarked": attack_psnr,
                                            "NC": f"{correlation:.4f}",
                                            "BER": f"{bit_error_rate:.4f}",
                                            "Status": status,
                                        }
                                    )
                                    if len(selected_attacks) == 1:
                                        before, after = st.columns(2)
                                        before.image(watermarked, caption="Before Attack", use_container_width=True)
                                        after.image(attacked, caption=f"After Attack · {attack_name}", use_container_width=True)
                                        st.caption(f"Extracted watermark: {extracted}")
                                    else:
                                        with st.expander(f"Result preview · {attack_name}"):
                                            before, after = st.columns(2)
                                            before.image(watermarked, caption="Before Attack", use_container_width=True)
                                            after.image(attacked, caption=f"After Attack · {attack_name}", use_container_width=True)
                                            st.caption(f"Extracted watermark: {extracted}")
                                    st.download_button(
                                        f"Download · {attack_name}",
                                        image_bytes(attacked, output_format),
                                        file_name=f"attacked_{attack_name.lower().replace(' ', '_').replace('%', 'pct').replace('+', 'plus')}.{extension}",
                                        mime="image/jpeg" if output_format == "JPEG" else "image/png",
                                        key=f"download_attack_{index}_{attack_name}",
                                    )

                            st.markdown("### Attack Result")
                            st.caption("PSNR is shown only when input and output dimensions match.")
                            st.table(result_rows)
                        except (ValueError, OSError, UnidentifiedImageError) as error:
                            show_error(str(error))
        else:
                st.markdown('<div class="wg-section-heading">Recovery</div>', unsafe_allow_html=True)
                st.caption("Recover the embedded text from a watermarked or attacked image.")
                with st.container(border=True):
                    recovery_upload = st.file_uploader(
                        "Upload Attacked Image", type=["png", "jpg", "jpeg"], key="recovery_image"
                    )
                    if recovery_upload:
                        try:
                            recovery_preview = load_image(recovery_upload)
                            st.image(recovery_preview, caption=recovery_upload.name, use_container_width=True)
                        except ValueError as error:
                            show_error(str(error))
                    recovery_secret = st.text_input("Secret key", type="password", key="recovery_secret")
                    expected_text = st.text_input(
                        "Expected watermark text", "Farrel - NPM 43", key="recovery_expected"
                    )
                    recovery_clicked = st.button(
                        "Recover Watermark",
                        type="primary",
                        disabled=recovery_upload is None,
                        use_container_width=True,
                    )

                if recovery_clicked:
                    if not recovery_secret.strip():
                        show_error("Secret key wajib diisi.")
                    elif not expected_text:
                        show_error("Expected watermark text wajib diisi untuk perhitungan NC dan BER.")
                    else:
                        try:
                            with st.spinner("Extracting watermark..."):
                                image = load_image(recovery_upload)
                                extracted, correlation, bit_error_rate = get_recovery_metrics(
                                    image, expected_text, recovery_secret
                                )
                                status = watermark_status(correlation, bit_error_rate)
                            st.markdown("### Recovery Result")
                            with st.container(border=True):
                                before, details = st.columns([1.4, 1])
                                before.image(image, caption="Uploaded image", use_container_width=True)
                                with details:
                                    st.markdown("**Expected watermark**")
                                    st.write(expected_text)
                                    st.markdown("**Recovered watermark**")
                                    st.write(extracted or "(text unreadable)")
                                    st.metric("NC", f"{correlation:.4f}")
                                    st.metric("BER", f"{bit_error_rate:.4f}")
                                if status == "Watermark Detected / Recovered":
                                    show_status("detected", "✓ Watermark Recovered")
                                elif status == "Watermark Partially Recovered":
                                    show_status("partial", "Watermark Partially Recovered")
                                else:
                                    show_status("missing", "× Watermark Not Recovered")
                        except (ValueError, OSError, UnidentifiedImageError) as error:
                            show_error(str(error))

    st.markdown(
        '<footer class="wg-footer">WatermarkGuard - Digital Watermark Protection - Robust DCT</footer>',
        unsafe_allow_html=True,
    )