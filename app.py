"""Run with streamlit run app.py."""

from html import escape
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
import streamlit as st

import stego_dct
import stego_lsb
from stego_text import MEMO, PAIRS, PATTERN, embed_id, extract_id, votes_for

RECIPIENTS = {1: "Asha", 2: "Ravi", 3: "Neha", 4: "Karan", 5: "Meera"}
METHODS = {"LSB": stego_lsb, "DCT": stego_dct}
IMAGE_TYPES = ["png", "jpg", "jpeg"]
SAMPLE = Path(__file__).with_name("samples") / "blue-marble.jpg"


def read_image(source):
    with Image.open(source) as image:
        return np.array(image.convert("RGB"))


def show_memos(original, recipient_id):
    def highlight(match):
        word = escape(match[0])
        changed = escape(embed_id(match[0], recipient_id))
        return f"<mark>{changed}</mark>" if changed != word else word

    left, right = st.columns(2)
    left.caption("Original memo")
    left.text(original)
    right.caption("Personalized memo")
    marked = PATTERN.sub(highlight, escape(original))
    right.html(f'<div style="white-space: pre-wrap; overflow-wrap: anywhere">{marked}</div>')


def sender():
    memo = st.text_area("Memo", MEMO, height=100)
    left, right = st.columns(2)
    recipient = left.selectbox("Recipient", RECIPIENTS, format_func=RECIPIENTS.get)
    method = right.radio("Sender method", METHODS, horizontal=True)
    cover_upload = st.file_uploader("Cover image (optional, uses Blue Marble by default)", type=IMAGE_TYPES)
    st.subheader("1. Recipient fingerprint")
    st.write(f"{RECIPIENTS[recipient]} · ID {recipient} · `{recipient:08b}`")
    st.subheader("2. Memo wording")
    missing = [" / ".join(pair) for pair, votes in zip(PAIRS, votes_for(memo)) if not any(votes)]
    st.caption(f"{len(PAIRS) - len(missing)}/{len(PAIRS)} synonym pairs present")
    if missing:
        st.warning("Add a word from each missing pair: " + ", ".join(missing))
    show_memos(memo, recipient)
    if missing:
        return

    personalised = embed_id(memo, recipient)
    used = len(personalised.encode("utf-8"))
    st.subheader("3. Image embedding")
    try:
        cover = read_image(cover_upload if cover_upload is not None else SAMPLE)
        capacity = METHODS[method].capacity_bytes(cover)
        st.caption(f"Capacity used: {used:,} of {capacity:,} bytes")
        stego = METHODS[method].embed(cover, personalised)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        st.error(f"Could not create the stego image. {error}")
        return
    delta = np.abs(stego.astype(np.int16) - cover)
    mse = np.mean(delta.astype(float) ** 2)
    psnr = 10 * np.log10(255**2 / mse) if mse else float("inf")
    difference = (delta * 50).clip(0, 255).astype(np.uint8)
    captions = ("Cover", "Stego image", "Difference ×50")
    for column, image, caption in zip(st.columns(3), (cover, stego, difference), captions):
        column.image(image, caption=caption)
    st.caption(f"PSNR: {psnr:.2f} dB")
    png = BytesIO()
    Image.fromarray(stego).save(png, format="PNG")
    data = png.getvalue()
    st.session_state.sent = (data, method)
    label = f"Download {method} PNG for {RECIPIENTS[recipient]}"
    filename = f"leaktrace-{recipient}-{method.lower()}.png"
    st.download_button(label, data, filename, "image/png", on_click="ignore")


def receiver():
    upload = st.file_uploader("Stego image", type=IMAGE_TYPES)
    sent_png, sent_method = st.session_state.get("sent", (None, "LSB"))
    if upload is None and sent_png:
        st.caption(f"Using the latest Sender image ({sent_method}).")
    method = st.radio("Extraction method", METHODS, index=list(METHODS).index(sent_method), horizontal=True)
    if st.button("Extract", disabled=upload is None and sent_png is None):
        try:
            source = upload if upload is not None else BytesIO(sent_png)
            st.text(METHODS[method].extract(read_image(source)))
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            st.error(str(error))


def trace():
    with st.form("leak_trace", border=False):
        leaked = st.text_area("Paste the leaked message", height=140)
        submitted = st.form_submit_button("Trace leak")
    if not submitted:
        return
    recipient, bits = extract_id(leaked)
    rows = []
    for pair, votes, bit in zip(PAIRS, votes_for(leaked), bits):
        words = ", ".join(word for word, count in zip(pair, votes) if count)
        rows.append({"Pair": " / ".join(pair), "Found": words or "Not found", "Bit": "?" if bit is None else str(bit)})
    st.table(rows)
    st.write("Recovered bits · `" + "".join("?" if bit is None else str(bit) for bit in bits) + "`")
    if recipient is None:
        st.warning("Could not recover the full ID. Some synonym pairs are missing or tied.")
    elif recipient not in RECIPIENTS:
        st.warning(f"ID {recipient} is not registered.")
    else:
        st.success(f"Leak traced to: {RECIPIENTS[recipient]} (ID {recipient})")
        st.caption("The result identifies a matching distributed copy.")


st.set_page_config(page_title="LeakTrace", layout="wide")
st.title("LeakTrace")
send_tab, receive_tab, trace_tab = st.tabs(["Sender", "Recipient", "Leak Trace"])
with send_tab:
    sender()
with receive_tab:
    receiver()
with trace_tab:
    trace()
