"""Hide text in one frequency coefficient per 8-by-8 image block."""

import numpy as np
from scipy.fft import dctn, idctn

from stego_lsb import HEADER_BITS, decode_message, message_length, pack_message

Q = 30
REPEAT = 3
ROW, COL = 4, 3
LUMINANCE = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def capacity_bytes(img):
    # The first two shape entries are height and width. // rounds down to whole blocks.
    height, width = img.shape[:2]
    blocks = (height // 8) * (width // 8)
    return max(0, (blocks // REPEAT - HEADER_BITS) // 8)


def block_pixels(img, offset, count):
    # divmod gives the row (quotient) and column (remainder) of each block number.
    block_rows, block_cols = np.divmod(np.arange(offset, offset + count), img.shape[1] // 8)
    # None inserts a length-one axis. Broadcasting pairs every row and column
    # within each block, so the two arrays index a (count, 8, 8) grid.
    rows = 8 * block_rows[:, None, None] + np.arange(8)[None, :, None]
    cols = 8 * block_cols[:, None, None] + np.arange(8)[None, None, :]
    return rows, cols


def embed(img, text):
    # repeat duplicates each individual bit three times before moving to the next bit.
    bits = np.repeat(pack_message(text, capacity_bytes(img)), REPEAT)
    pixels = block_pixels(img, 0, bits.size)
    # A change of Q in this coefficient can shift a pixel by at most Q / 4.
    margin = (Q + 3) // 4
    # pixels is the (rows, cols) tuple. Tuple indexing gathers whole RGB pixels.
    rgb = img[pixels].clip(margin, 255 - margin)
    # @ takes the dot product of each RGB triple with the luminance weights.
    brightness = rgb @ LUMINANCE
    # Negative axes count from the end. Transform each 8-by-8 block on its own.
    coeffs = dctn(brightness, axes=(-2, -1), norm="ortho")
    # The first : selects the same coefficient from every block.
    scaled = coeffs[:, ROW, COL] / Q
    # Every valid index has the form 2*k + bit. rint rounds k to the nearest integer.
    index = 2 * np.rint((scaled - bits) / 2) + bits
    coeffs[:, ROW, COL] = index * Q
    delta = idctn(coeffs, axes=(-2, -1), norm="ortho") - brightness
    stego = img.copy()
    # ... keeps the existing axes. The new final axis broadcasts the change to R, G, and B.
    stego[pixels] = np.rint(rgb + delta[..., None]).clip(0, 255).astype(np.uint8)
    return stego


def read_bits(img, offset, count):
    pixels = block_pixels(img, offset * REPEAT, count * REPEAT)
    coeffs = dctn(img[pixels] @ LUMINANCE, axes=(-2, -1), norm="ortho")
    # Modulo 2 maps even indices to 0 and odd ones to 1.
    raw = np.rint(coeffs[:, ROW, COL] / Q).astype(int) % 2
    # -1 lets NumPy infer the number of groups. Summing across each row counts its 1s.
    return raw.reshape(-1, REPEAT).sum(axis=1) > REPEAT // 2


def extract(img):
    capacity = capacity_bytes(img)
    # The inline if/else skips block indexing when the image has zero memo capacity.
    header = read_bits(img, 0, HEADER_BITS) if capacity else np.empty(0, dtype=np.uint8)
    length = message_length(header, capacity)
    return decode_message(read_bits(img, HEADER_BITS, 8 * length))
