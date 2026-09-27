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

st.markdown(
    """
    <style>
    :root {
        --color-main: #000000;
        --color-secondary: #233D4D;
        --color-third: #FE7F2D;
        --color-fourth: #EAECF0;
    }
    html, body, #root, [data-testid="stApp"],
    [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stMainBlockContainer"], .block-container,
    [data-testid="stHeader"] {
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    html, body, #root, [data-testid="stApp"], [data-testid="stAppViewContainer"] {
        min-height: 100%;
        width: 100%;
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
    .st-key-top_navbar {
        position: relative;
        display: block;
        width: 100%;
        min-height: 64px;
        box-sizing: border-box;
        margin: 0 0 1.7rem;
        padding: .45rem 2rem;
        overflow: visible;
        background-color: var(--color-secondary);
        border-bottom: 2px solid var(--color-third);
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
    .wg-brand {
        display: flex;
        align-items: center;
        gap: .6rem;
        min-height: 2.5rem;
    }
    .wg-mark {
        display: grid;
        width: 2rem;
        height: 2rem;
        flex: 0 0 2rem;
        place-items: center;
        border: 1px solid var(--color-third);
        border-radius: 4px;
        background-color: var(--color-third);
        color: var(--color-main);
        font-weight: 800;
        font-size: .78rem;
    }
    .wg-brand-name {
        color: var(--color-fourth);
        font-size: .96rem;
        font-weight: 700;
        white-space: nowrap;
    }

    [data-baseweb="popover"] {
        border: 1px solid var(--color-secondary);
        background-color: var(--color-fourth);
    }
    [data-baseweb="popover"] [data-testid="stCaptionContainer"] {
        display: none;
    }
    [data-baseweb="popover"] [data-testid="stButton"] button {
        width: 100%;
        min-height: 2.35rem;
        border: 1px solid var(--color-secondary);
        border-radius: 4px;
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    [data-baseweb="popover"] [data-testid="stButton"] button:hover,
    [data-baseweb="popover"] [data-testid="stButton"] button[kind="primary"] {
        border-color: var(--color-third);
        background-color: var(--color-third);
        color: var(--color-main);
    }

    .st-key-wg_content {
        width: 100%;
        max-width: 1160px;
        box-sizing: border-box;
        margin: 0 auto;
        padding: 0 2rem 2.5rem;
    }
    .st-key-wg_content > [data-testid="stVerticalBlock"] { gap: 1rem; }
    .wg-page-header { margin: .1rem 0 .25rem; }
    .wg-page-header h1 {
        margin: 0;
        color: var(--color-main);
        font-size: clamp(1.55rem, 2.4vw, 1.9rem);
        line-height: 1.25;
        font-weight: 700;
    }
    .wg-page-header p { margin: .35rem 0 0; color: var(--color-secondary); font-size: .95rem; }
    h2, h3, [data-testid="stWidgetLabel"] p, label { color: var(--color-main); }
    p, small, [data-testid="stCaptionContainer"] { color: var(--color-secondary); }
    .wg-section-heading {
        margin: 0 0 .65rem;
        color: var(--color-main);
        font-size: 1rem;
        line-height: 1.35;
        font-weight: 650;
    }
    .wg-section-description { margin: 0 0 .8rem; color: var(--color-secondary); font-size: .88rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--color-secondary);
        border-radius: 5px;
        background-color: var(--color-fourth);
    }
    [data-testid="stFileUploader"], [data-testid="stFileUploaderDropzone"] {
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    [data-testid="stFileUploaderDropzone"] {
        min-height: 8rem;
        border: 1px dashed var(--color-secondary);
        border-radius: 4px;
    }
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] span { color: var(--color-main); }
    [data-testid="stFileUploaderDropzone"] small { color: var(--color-secondary); }
    [data-testid="stFileUploaderDropzone"] svg { color: var(--color-third); fill: var(--color-third); }
    [data-testid="stFileUploaderDropzone"] button {
        border: 1px solid var(--color-third);
        border-radius: 4px;
        background-color: var(--color-third);
        color: var(--color-main);
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        border-color: var(--color-secondary);
        background-color: var(--color-secondary);
        color: var(--color-fourth);
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        min-height: 2.45rem;
        border: 1px solid var(--color-secondary);
        border-radius: 4px;
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stTextArea"] textarea::placeholder { color: var(--color-secondary); }
    [data-testid="stTextInput"] button {
        border: 1px solid var(--color-secondary);
        border-radius: 0 4px 4px 0;
        background-color: var(--color-secondary);
        color: var(--color-fourth);
    }
    [data-testid="stTextInput"] button svg { color: var(--color-fourth); fill: var(--color-fourth); }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
        border-color: var(--color-third);
        outline: 2px solid var(--color-third);
    }
    [data-testid="stTextInput"] svg,
    [data-testid="stSelectbox"] svg,
    [data-testid="stMultiSelect"] svg { color: var(--color-secondary); fill: var(--color-secondary); }
    input[type="radio"], input[type="checkbox"] { accent-color: var(--color-third); }
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label { color: var(--color-main); }
    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
        min-height: 2.55rem;
        border: 1px solid var(--color-secondary);
        border-radius: 4px;
        color: var(--color-main);
        font-weight: 650;
    }
    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] button {
        border-color: var(--color-third);
        background-color: var(--color-third);
        color: var(--color-main);
    }
    [data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stDownloadButton"] button:hover {
        border-color: var(--color-secondary);
        background-color: var(--color-secondary);
        color: var(--color-fourth);
    }
    [data-testid="stButton"] button[kind="secondary"] {
        border-color: var(--color-secondary);
        background-color: var(--color-secondary);
        color: var(--color-fourth);
    }
    [data-testid="stButton"] button[kind="secondary"]:hover {
        border-color: var(--color-third);
        background-color: var(--color-third);
        color: var(--color-main);
    }
    [data-testid="stButton"] button:disabled {
        border-color: var(--color-secondary);
        background-color: var(--color-fourth);
        color: var(--color-secondary);
    }
    [data-testid="stMetric"] {
        border-left: 3px solid var(--color-third);
        background-color: var(--color-fourth);
        padding: .3rem .8rem;
    }
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--color-main); }
    [data-testid="stAlert"] {
        border: 1px solid var(--color-secondary);
        border-left: 4px solid var(--color-third);
        border-radius: 4px;
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    [data-testid="stAlert"] p, [data-testid="stAlert"] span { color: var(--color-main); }
    [data-testid="stAlert"] svg { color: var(--color-third); fill: var(--color-third); }
    [data-baseweb="popover"], [data-baseweb="menu"],
    [role="listbox"], [role="option"] {
        border-color: var(--color-secondary);
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    [data-baseweb="popover"] [data-testid="stButton"] button {
        width: 100%;
        border: 1px solid var(--color-secondary);
        border-radius: 4px;
        background-color: var(--color-fourth);
        color: var(--color-main);
    }
    [data-baseweb="popover"] [data-testid="stButton"] button:hover,
    [data-baseweb="popover"] [data-testid="stButton"] button[kind="primary"],
    [role="option"]:hover, [role="option"][aria-selected="true"] {
        border-color: var(--color-third);
        background-color: var(--color-third);
        color: var(--color-main);
    }
    [data-testid="stProgressBar"] div { background-color: var(--color-third); }
    [data-testid="stSpinner"] svg { color: var(--color-third); }
    [data-testid="stTable"] { overflow-x: auto; }
    [data-testid="stTable"] table { border-collapse: collapse; background-color: var(--color-fourth); }
    [data-testid="stTable"] th {
        background-color: var(--color-secondary);
        color: var(--color-fourth);
        border-color: var(--color-secondary);
    }
    [data-testid="stTable"] td {
        background-color: var(--color-fourth);
        color: var(--color-main);
        border-color: var(--color-secondary);
    }
    .wg-result-status {
        margin-top: .8rem;
        padding: .75rem .9rem;
        border: 1px solid var(--color-secondary);
        border-left: 4px solid var(--color-third);
        border-radius: 4px;
        font-weight: 650;
    }
    .wg-result-detected { background-color: var(--color-third); color: var(--color-main); }
    .wg-result-partial { background-color: var(--color-secondary); color: var(--color-fourth); }
    .wg-result-missing { background-color: var(--color-fourth); color: var(--color-main); }
    .wg-footer {
        margin-top: .5rem;
        padding-top: .75rem;
        border-top: 1px solid var(--color-secondary);
        color: var(--color-secondary);
        font-size: .82rem;
    }
    a { color: var(--color-secondary); }
    *:focus-visible { outline: 2px solid var(--color-third); }

    .st-key-top_navbar [data-testid="stButton"] > button,
    .st-key-top_navbar [data-testid="stPopover"] button {
        width: 100% !important;
        min-height: 2.5rem !important;
        padding: .45rem .85rem !important;
        border: 1px solid transparent !important;
        border-radius: 5px !important;
        background: var(--color-secondary) !important;
        background-color: var(--color-secondary) !important;
        color: var(--color-fourth) !important;
        font-size: .86rem !important;
        font-weight: 650 !important;
        white-space: nowrap !important;
        box-shadow: none !important;
        text-shadow: none !important;
        appearance: none !important;
    }
    .st-key-top_navbar [data-testid="stButton"] > button[kind="primary"] {
        background: var(--color-third) !important;
        background-color: var(--color-third) !important;
        color: var(--color-main) !important;
        border-color: var(--color-third) !important;
    }
    .st-key-top_navbar [data-testid="stPopover"] button {
        background: var(--color-secondary) !important;
        background-color: var(--color-secondary) !important;
        color: var(--color-fourth) !important;
        border-color: transparent !important;
    }
    .st-key-top_navbar [data-testid="stPopover"] button[kind="primary"] {
        background: var(--color-third) !important;
        background-color: var(--color-third) !important;
        color: var(--color-main) !important;
        border-color: var(--color-third) !important;
    }
    .st-key-top_navbar [data-testid="stButton"] > button:hover,
    .st-key-top_navbar [data-testid="stPopover"] button:hover {
        background: var(--color-third) !important;
        background-color: var(--color-third) !important;
        color: var(--color-main) !important;
        border-color: var(--color-third) !important;
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

    @media (max-width: 900px) {
        .st-key-top_navbar {
            padding: .5rem 1rem;
        }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] {
            gap: .5rem;
        }
        .st-key-top_navbar [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            min-width: 0;
        }
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
            flex: 0 0 3rem;
        }
        .st-key-wg_content {
            padding: 0 1rem 2rem;
        }
        .wg-page-header {
            margin-bottom: .2rem;
        }
        .wg-page-header p {
            font-size: .9rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
                        show_status("detected", "Watermark Created")
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
