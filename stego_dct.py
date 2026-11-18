"""Hide text in one frequency coefficient per 8-by-8 image block."""

import numpy as np
from scipy.fft import dctn, idctn

from stego_lsb import HEADER_BITS, decode_message, message_length, pack_message

Q = 30
REPEAT = 3
ROW, COL = 4, 3
LUMINANCE = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def capacity_bytes(img):
    height, width = img.shape[:2]
    blocks = (height // 8) * (width // 8)
    return max(0, (blocks // REPEAT - HEADER_BITS) // 8)


def block_pixels(img, offset, count):
    # Return pixel indices for successive blocks, ignoring incomplete edge blocks.
    block_rows, block_cols = np.divmod(np.arange(offset, offset + count), img.shape[1] // 8)
    rows = 8 * block_rows[:, None, None] + np.arange(8)[None, :, None]
    cols = 8 * block_cols[:, None, None] + np.arange(8)[None, None, :]
    return rows, cols


def embed(img, text):
    bits = np.repeat(pack_message(text, capacity_bytes(img)), REPEAT)
    pixels = block_pixels(img, 0, bits.size)
    # A change of Q in this coefficient can shift a pixel by at most Q / 4.
    margin = (Q + 3) // 4
    rgb = img[pixels].clip(margin, 255 - margin)
    brightness = rgb @ LUMINANCE
    coeffs = dctn(brightness, axes=(-2, -1), norm="ortho")
    scaled = coeffs[:, ROW, COL] / Q
    # Round to the nearest index whose parity matches the intended bit.
    index = 2 * np.rint((scaled - bits) / 2) + bits
    coeffs[:, ROW, COL] = index * Q
    delta = idctn(coeffs, axes=(-2, -1), norm="ortho") - brightness
    stego = img.copy()
    stego[pixels] = np.rint(rgb + delta[..., None]).clip(0, 255).astype(np.uint8)
    return stego


def read_bits(img, offset, count):
    pixels = block_pixels(img, offset * REPEAT, count * REPEAT)
    coeffs = dctn(img[pixels] @ LUMINANCE, axes=(-2, -1), norm="ortho")
    raw = np.rint(coeffs[:, ROW, COL] / Q).astype(int) % 2
    return raw.reshape(-1, REPEAT).sum(axis=1) > REPEAT // 2


def extract(img):
    capacity = capacity_bytes(img)
    header = read_bits(img, 0, HEADER_BITS) if capacity else np.empty(0, dtype=np.uint8)
    length = message_length(header, capacity)
    return decode_message(read_bits(img, HEADER_BITS, 8 * length))
