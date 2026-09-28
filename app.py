import io
import hashlib
import secrets

import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError

from attacks.image_attacks import apply_attack
from metrics.metrics import ber, normalized_correlation, psnr, watermark_status
from watermark.dwt_dct_watermark import embed_watermark, extract_watermark_by_key


ATTACKS = [
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


def load_image(uploaded_file) -> Image.Image:
    """Decode an uploaded supported image and return an independent RGB image."""
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.load()
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError("File tidak dapat dibaca sebagai gambar PNG atau JPEG yang valid.") from error


def image_bytes(image: Image.Image, image_format: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def navigate_to(page: str) -> None:
    st.session_state["active_page"] = page


def render_status(kind: str, message: str) -> None:
    st.markdown(
        f'<div class="wg-status wg-status-{kind}"><span>{message}</span></div>',
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="WatermarkGuard", layout="wide")
st.session_state.setdefault("active_page", "Create Watermark")
st.session_state.setdefault("attack_mode", "Single Attack")
st.session_state.setdefault("multiple_attack_results", [])
st.session_state.setdefault("multiple_attack_signature", None)
st.session_state.setdefault("created_watermark_results", [])
st.session_state.setdefault("created_watermark_signature", None)
st.session_state.pop("create_images", None)
st.session_state.pop("create_upload_generation", None)
st.session_state.pop("create_upload_overflow", None)
for state_key in tuple(st.session_state.keys()):
    if state_key.startswith("create_images_uploader_"):
        st.session_state.pop(state_key, None)
if st.session_state["active_page"] not in {"Create Watermark", "Detect Watermark", "Attack"}:
    st.session_state["active_page"] = "Attack"

# --- UI/UX CSS UPDATE KETIGA (AURORA GLASSMORPHISM POLISHED) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        /* Warna Dasar & Glassmorphism yang lebih premium */
        --color-glass-bg: rgba(15, 23, 42, 0.55);
        --color-glass-border: rgba(255, 255, 255, 0.12);
        
        /* Tipografi */
        --color-text-main: #f8fafc;
        --color-text-muted: #cbd5e1; /* Dibuat sedikit lebih terang agar lebih mudah dibaca */
        
        /* Aksen Gradasi Modern (Biru - Ungu - Pink) */
        --color-primary-grad: linear-gradient(135deg, #4f46e5 0%, #9333ea 50%, #e879f9 100%);
        --color-primary-grad-hover: linear-gradient(135deg, #4338ca 0%, #7e22ce 50%, #d946ef 100%);
        
        /* Status Warna Pastel Neon */
        --color-success-bg: rgba(16, 185, 129, 0.15);
        --color-success-border: #10b981;
        --color-warning-bg: rgba(245, 158, 11, 0.15);
        --color-warning-border: #f59e0b;
        --color-danger-bg: rgba(239, 68, 68, 0.15);
        --color-danger-border: #ef4444;
    }

    /* Background Aplikasi: Mesh Gradient yang lebih hidup namun lembut */
    html, body, #root, [data-testid="stApp"],
    [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stMainBlockContainer"], .block-container,
    [data-testid="stHeader"] {
        background-color: #080b13 !important; /* Warna dasar sangat gelap untuk kontras maksimal */
        background-image: 
            radial-gradient(circle at 15% 25%, rgba(79, 70, 229, 0.18) 0%, transparent 45%),
            radial-gradient(circle at 85% 15%, rgba(217, 70, 239, 0.15) 0%, transparent 45%),
            radial-gradient(circle at 75% 85%, rgba(14, 165, 233, 0.15) 0%, transparent 50%),
            radial-gradient(circle at 20% 90%, rgba(16, 185, 129, 0.12) 0%, transparent 45%) !important;
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
        background: rgba(8, 11, 19, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-bottom: 1px solid var(--color-glass-border) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
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
        box-shadow: 0 4px 15px rgba(147, 51, 234, 0.4);
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
        background: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(25px) !important;
        border: 1px solid var(--color-glass-border) !important;
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6) !important;
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
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.4);
        padding: 1.5rem !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(255, 255, 255, 0.25);
        box-shadow: 0 10px 40px -10px rgba(147, 51, 234, 0.15);
    }

    /* File Uploader */
    [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"] {
        background-color: transparent;
    }
    [data-testid="stFileUploaderDropzone"] {
        min-height: 8rem;
        background: rgba(15, 23, 42, 0.6) !important;
        border: 2px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    .st-key-create_image [data-testid="stFileUploaderDropzone"] {
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    .st-key-detect_image [data-testid="stFileUploaderDropzone"] {
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    .st-key-attack_image [data-testid="stFileUploaderDropzone"] {
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
    }
    .st-key-create_image [data-testid="stFileUploaderDropzoneInstructions"] {
        flex: 0 1 auto;
        justify-content: center;
        text-align: center;
    }
    .st-key-detect_image [data-testid="stFileUploaderDropzoneInstructions"] {
        flex: 0 1 auto;
        justify-content: center;
        text-align: center;
    }
    .st-key-attack_image [data-testid="stFileUploaderDropzoneInstructions"] {
        flex: 0 1 auto;
        justify-content: center;
        text-align: center;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #e879f9 !important;
        background: rgba(232, 121, 249, 0.08) !important;
    }
    [data-testid="stFileUploaderDropzone"] svg { color: #e879f9; fill: #e879f9; }
    
    /* Text Inputs, TextAreas, Selectboxes */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        min-height: 2.75rem;
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px;
        color: var(--color-text-main) !important;
        transition: all 0.25s ease;
    }
    [data-testid="stTextInput"] input::placeholder { color: #94a3b8; }
    [data-testid="stTextInput"] button { border: none; background-color: transparent; }
    [data-testid="stTextInput"] button svg { color: var(--color-text-muted); fill: var(--color-text-muted); }
    
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
        border-color: #e879f9 !important;
        box-shadow: 0 0 0 3px rgba(232, 121, 249, 0.25) !important;
        outline: none;
    }

    input[type="radio"], input[type="checkbox"] { accent-color: #9333ea; }
    
    /* =========================================================
       FIX WARNA TEKS BUTTON AGAR PASTI TERBACA & TIDAK HITAM
       ========================================================= */
    [data-testid="stButton"] button p,
    [data-testid="stButton"] button span,
    [data-testid="stDownloadButton"] button p,
    [data-testid="stDownloadButton"] button span,
    [data-testid="stPopover"] button p,
    [data-testid="stPopover"] button span,
    [data-testid="stFileUploaderDropzone"] button p,
    [data-testid="stFileUploaderDropzone"] button span {
        color: #ffffff !important;
        font-weight: 600 !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4) !important; /* Bayangan agar kontras */
    }

    /* Buttons Primary (TOMBOL GRADASI KEREN) */
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] button {
        min-height: 2.75rem;
        background: var(--color-primary-grad) !important;
        border: none !important;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(147, 51, 234, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stDownloadButton"] button:hover {
        background: var(--color-primary-grad-hover) !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(147, 51, 234, 0.5) !important;
    }
    
    /* Buttons Secondary */
    [data-testid="stButton"] button[kind="secondary"],
    [data-testid="stFileUploaderDropzone"] button {
        min-height: 2.75rem;
        background: rgba(30, 41, 59, 0.8) !important; /* Dibuat gelap agar teks putih terbaca */
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px;
        transition: all 0.2s ease;
    }
    [data-testid="stButton"] button[kind="secondary"]:hover,
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: rgba(51, 65, 85, 0.9) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
    }
    [data-testid="stButton"] button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        transform: none !important;
    }

    /* Metrics Box */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid var(--color-glass-border);
        border-left: 4px solid #9333ea;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }
    [data-testid="stMetric"] label { color: var(--color-text-muted) !important; font-size: 0.9rem; font-weight: 600; }
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--color-text-main) !important; font-weight: 800; }

    /* Progress & Spinner */
    [data-testid="stProgressBar"] div { background: var(--color-primary-grad); }
    [data-testid="stSpinner"] svg { color: #e879f9; }

    /* Tables dengan Tema Transparan */
    [data-testid="stTable"] { overflow-x: auto; border-radius: 12px; border: 1px solid var(--color-glass-border); }
    [data-testid="stTable"] table { border-collapse: collapse; background: rgba(15, 23, 42, 0.6); width: 100%; }
    [data-testid="stTable"] th {
        background: rgba(255, 255, 255, 0.08);
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
    .wg-result-detected { background: var(--color-success-bg); color: #34d399; border: 1px solid var(--color-success-border); box-shadow: 0 0 20px rgba(16, 185, 129, 0.25); }
    .wg-result-partial { background: var(--color-warning-bg); color: #fbbf24; border: 1px solid var(--color-warning-border); box-shadow: 0 0 20px rgba(245, 158, 11, 0.25); }
    .wg-result-missing { background: var(--color-danger-bg); color: #f87171; border: 1px solid var(--color-danger-border); box-shadow: 0 0 20px rgba(239, 68, 68, 0.25); }

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
    
    a { color: #e879f9; text-decoration: none; transition: color 0.2s; }
    a:hover { color: #f0abfc; }
    *:focus-visible { outline: 2px solid #e879f9; }

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
        box-shadow: none !important;
        transition: all 0.3s ease !important;
    }
    /* Pastikan teks tombol Navbar juga di-override putih */
    .st-key-top_navbar [data-testid="stButton"] p,
    .st-key-top_navbar [data-testid="stPopover"] p {
        color: #cbd5e1 !important; /* Agak redup saat tidak aktif */
        font-weight: 600 !important;
        text-shadow: none !important;
    }
    .st-key-top_navbar [data-testid="stButton"] > button:hover p,
    .st-key-top_navbar [data-testid="stPopover"] button:hover p {
        color: #ffffff !important; /* Putih bersih saat di-hover */
    }
    
    .st-key-top_navbar [data-testid="stButton"] > button:hover,
    .st-key-top_navbar [data-testid="stPopover"] button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
    }
    
    /* Aktif State di Navbar */
    .st-key-top_navbar [data-testid="stButton"] > button[kind="primary"],
    .st-key-top_navbar [data-testid="stPopover"] button[kind="primary"] {
        background: rgba(255, 255, 255, 0.15) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: inset 0 0 20px rgba(255, 255, 255, 0.08) !important;
    }
    /* Teks Aktif di Navbar */
    .st-key-top_navbar [data-testid="stButton"] > button[kind="primary"] p,
    .st-key-top_navbar [data-testid="stPopover"] button[kind="primary"] p {
        color: #ffffff !important;
        text-shadow: 0 0 8px rgba(255, 255, 255, 0.4) !important;
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
# --- AKHIR DARI UPDATE CSS ---

active_page = st.session_state["active_page"]

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
        st.button(
            "Attack",
            type="primary" if active_page == "Attack" else "secondary",
            use_container_width=True,
            key="nav_attack",
            on_click=navigate_to,
            args=("Attack",),
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
                "Upload Cover Image",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=False,
                key="create_image",
            )
            if create_upload:
                try:
                    cover_preview = load_image(create_upload)
                    preview_columns = st.columns([1, 2, 1])
                    preview_columns[1].image(
                        cover_preview,
                        caption=create_upload.name,
                        width="stretch",
                    )
                except ValueError as error:
                    show_error(str(error))

        with st.container(border=True):
            st.markdown('<div class="wg-section-heading">2. Watermark information</div>', unsafe_allow_html=True)
            watermark_text = st.text_input(
                "Watermark text / owner identity",
                value="",
                key="watermark_text",
                autocomplete="off",
            )
            st.caption("The text is embedded invisibly using keyed hybrid DWT-DCT coefficients. A secure secret key is generated automatically.")

        upload_signature = (
            (create_upload.name, hashlib.sha256(create_upload.getvalue()).hexdigest())
            if create_upload
            else None
        )
        create_signature = (upload_signature, watermark_text)
        if st.session_state["created_watermark_signature"] != create_signature:
            st.session_state["created_watermark_results"] = []
            st.session_state["created_secret_key"] = None
            st.session_state["created_watermark_signature"] = create_signature

        create_clicked = st.button(
            "Create Watermark",
            type="primary",
            disabled=create_upload is None,
            use_container_width=True,
        )
        if create_clicked:
            if not watermark_text:
                show_error("Teks watermark wajib diisi.")
            else:
                secret = secrets.token_urlsafe(32)
                created_results = []
                with st.spinner("Creating watermarks..."):
                    try:
                        original = load_image(create_upload)
                        watermarked, _ = embed_watermark(
                            original, watermark_text, secret
                        )
                        original_array = np.asarray(original)
                        watermarked_array = np.asarray(watermarked)
                        difference = np.max(
                            np.abs(
                                original_array.astype(np.int16)
                                - watermarked_array.astype(np.int16)
                            ),
                            axis=2,
                        )
                        difference_map = np.clip(difference * 8, 0, 255).astype(
                            np.uint8
                        )
                        created_results.append(
                            {
                                "name": create_upload.name,
                                "original_bytes": image_bytes(original, "PNG"),
                                "watermarked_bytes": image_bytes(watermarked, "PNG"),
                                "difference_bytes": image_bytes(
                                    Image.fromarray(difference_map), "PNG"
                                ),
                                "psnr": psnr(original_array, watermarked_array),
                                "error": None,
                            }
                        )
                    except (ValueError, OSError, UnidentifiedImageError) as error:
                        created_results.append(
                            {
                                "name": create_upload.name,
                                "error": str(error),
                            }
                        )
                st.session_state["created_watermark_results"] = created_results
                st.session_state["created_secret_key"] = secret if any(
                    result["error"] is None for result in created_results
                ) else None

        created_results = st.session_state["created_watermark_results"]
        if created_results:
            st.markdown("### Results")
            for index, result in enumerate(created_results, start=1):
                with st.container(border=True):
                    st.markdown(f"#### {result['name']}")
                    if result["error"]:
                        show_error(result["error"])
                        continue

                    original_column, watermarked_column = st.columns(2)
                    original_column.image(
                        result["original_bytes"],
                        caption="Original Image",
                        width="stretch",
                    )
                    watermarked_column.image(
                        result["watermarked_bytes"],
                        caption="Watermarked Image",
                        width="stretch",
                    )
                    metric_column, info_column = st.columns([1, 2])
                    metric_column.metric("PSNR", f"{result['psnr']:.2f} dB")
                    info_column.markdown(f"**Watermark created**  \n{watermark_text}")
                    show_status("detected", "\u2713 Watermark Created")
                    with st.expander("View watermark effect"):
                        effect_preview_columns = st.columns([1, 2, 1])
                        effect_preview_columns[1].image(
                            result["difference_bytes"],
                            caption="Difference map \u00b7 changes amplified for visualization",
                            width="stretch",
                        )
                    file_stem = result["name"].rsplit(".", 1)[0]
                    st.download_button(
                        "Download Watermarked Image",
                        data=result["watermarked_bytes"],
                        file_name=f"{file_stem}_watermarked.png",
                        mime="image/png",
                        key=f"download_created_image_{index}",
                    )

        if st.session_state.get("created_secret_key"):
            st.markdown("### Secret Key")
            st.caption("Simpan key ini dengan aman. Key diperlukan untuk mendeteksi dan mengekstrak watermark.")
            st.code(st.session_state["created_secret_key"], language=None)

    elif active_page == "Detect Watermark":
        page_header("Detect Watermark", "Extract the owner identity using its secret key.")

        with st.container(border=True):
            st.markdown('<div class="wg-section-heading">Image and verification details</div>', unsafe_allow_html=True)
            detect_upload = st.file_uploader(
                "Upload Image", type=["png", "jpg", "jpeg"], key="detect_image"
            )
            if detect_upload:
                try:
                    detect_preview = load_image(detect_upload)
                    detect_preview_columns = st.columns([1, 2, 1])
                    detect_preview_columns[1].image(
                        detect_preview,
                        caption=detect_upload.name,
                        width="stretch",
                    )
                except ValueError as error:
                    show_error(str(error))
            detect_secret = st.text_input("Secret key", type="password", key="detect_secret")
            st.caption("Upload the watermarked image and enter the secret key used when it was created.")
            detect_clicked = st.button(
                "Detect Watermark",
                type="primary",
                disabled=detect_upload is None,
                use_container_width=True,
            )

        if detect_clicked:
            if not detect_secret.strip():
                show_error("Secret key wajib diisi.")
            else:
                try:
                    with st.spinner("Checking watermark..."):
                        image = load_image(detect_upload)
                        extracted, integrity_bits, expected_integrity_bits = extract_watermark_by_key(
                            image, detect_secret
                        )
                        if integrity_bits is None or expected_integrity_bits is None:
                            correlation = None
                            bit_error_rate = None
                            is_detected = False
                        else:
                            correlation = normalized_correlation(
                                expected_integrity_bits, integrity_bits
                            )
                            bit_error_rate = ber(expected_integrity_bits, integrity_bits)
                            is_detected = bool(
                                extracted is not None
                                and np.array_equal(integrity_bits, expected_integrity_bits)
                            )
                        status = "Watermark Detected" if is_detected else "Watermark Not Detected"
                    st.markdown("### Detection Result")
                    with st.container(border=True):
                        if status == "Watermark Detected":
                            show_status("detected", "✓ Watermark Detected")
                        elif status == "Watermark Partially Detected":
                            show_status("partial", "! Watermark Partially Detected · possibly altered")
                        else:
                            show_status("missing", "× Watermark Not Detected")
                        result_preview_columns = st.columns([1, 2, 1])
                        result_preview_columns[1].image(
                            image,
                            caption="Image checked",
                            width="stretch",
                        )
                        first, second = st.columns(2)
                        first.metric("NC integrity tag similarity", f"{correlation:.4f}" if correlation is not None else "N/A")
                        second.metric("BER integrity tag errors", f"{bit_error_rate:.4f}" if bit_error_rate is not None else "N/A")
                        st.markdown("**Owner Identity**")
                        st.markdown(f"{extracted if is_detected else '(not detected)'}")
                except (ValueError, OSError, UnidentifiedImageError) as error:
                    show_error(str(error))

    elif active_page == "Attack":
        page_header("Attack", "Apply image attacks to test watermark robustness.")
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
                    attack_preview_columns = st.columns([1, 2, 1])
                    attack_preview_columns[1].image(
                        attack_preview,
                        caption=attack_upload.name,
                        width="stretch",
                    )
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
            uploaded_bytes = attack_upload.getvalue() if attack_upload else None
            upload_signature = (
                attack_upload.name,
                hashlib.sha256(uploaded_bytes).hexdigest(),
            ) if attack_upload else None
            attack_signature = (
                upload_signature,
                mode,
                tuple(selected_attacks),
            )
            if st.session_state["multiple_attack_signature"] != attack_signature:
                st.session_state["multiple_attack_results"] = []
                st.session_state["multiple_attack_signature"] = attack_signature
            attack_clicked = st.button(
                "Apply Attack",
                type="primary",
                disabled=attack_upload is None,
                use_container_width=True,
            )

        single_attack_result = None
        if attack_clicked:
            if not selected_attacks:
                show_error("Pilih minimal satu jenis serangan.")
            else:
                try:
                    watermarked = load_image(attack_upload)
                    original_bytes = image_bytes(watermarked, "PNG")
                    multiple_results = []
                    if mode == "Multiple Attacks":
                        st.session_state["multiple_attack_results"] = []

                    with st.spinner("Applying attack..."):
                        for index, attack_name in enumerate(selected_attacks, start=1):
                            attacked = apply_attack(watermarked, attack_name)
                            output_format = "JPEG" if attack_name.startswith("JPEG") else "PNG"
                            extension = "jpg" if output_format == "JPEG" else "png"
                            result = {
                                "attack_name": attack_name,
                                "image_bytes": image_bytes(attacked, output_format),
                                "file_name": f"attacked_{attack_name.lower().replace(' ', '_').replace('%', 'pct').replace('+', 'plus')}.{extension}",
                                "mime_type": "image/jpeg" if output_format == "JPEG" else "image/png",
                            }

                            if mode == "Multiple Attacks":
                                multiple_results.append(result)
                            else:
                                single_attack_result = {
                                    "image": attacked,
                                    "result": result,
                                    "original": watermarked,
                                }

                    if mode == "Multiple Attacks":
                        st.session_state["multiple_attack_results"] = [
                            {
                                **result,
                                "original_bytes": original_bytes,
                            }
                            for result in multiple_results
                        ]
                except (ValueError, OSError, UnidentifiedImageError) as error:
                    show_error(str(error))

        if mode == "Multiple Attacks":
            multiple_results = st.session_state["multiple_attack_results"]
            if multiple_results:
                st.markdown("### Multiple Attack Results")
                for index, result in enumerate(multiple_results, start=1):
                    with st.expander(f"{index}. {result['attack_name']}"):
                        before, after = st.columns(2)
                        before.image(
                            result["original_bytes"],
                            caption="Original Watermarked Image",
                            width="stretch",
                        )
                        after.image(
                            result["image_bytes"],
                            caption="Attacked Image",
                            width="stretch",
                        )
                        st.download_button(
                            f"Download · {result['attack_name']}",
                            data=result["image_bytes"],
                            file_name=result["file_name"],
                            mime=result["mime_type"],
                            key=f"download_multiple_attack_{index}_{result['attack_name']}",
                        )
        elif single_attack_result is not None:
            st.markdown("### Attack Result")
            before, after = st.columns(2)
            before.image(
                single_attack_result["original"],
                caption="Original Watermarked Image",
                width="stretch",
            )
            after.image(
                single_attack_result["image"],
                caption="Attacked Image",
                width="stretch",
            )
            result = single_attack_result["result"]
            st.download_button(
                f"Download · {result['attack_name']}",
                data=result["image_bytes"],
                file_name=result["file_name"],
                mime=result["mime_type"],
                key=f"download_single_attack_{result['attack_name']}",
            )
    st.markdown(
        '<footer class="wg-footer">WatermarkGuard - Digital Watermark Protection - Hybrid DWT-DCT</footer>',
        unsafe_allow_html=True,
    )
