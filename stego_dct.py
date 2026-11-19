"""Hide text in one frequency coefficient per 8-by-8 image block."""

import numpy as np
from scipy.fft import dctn, idctn

from stego_lsb import HEADER_BITS, NO_MESSAGE, decode_message, message_length, pack_message

BLOCK_SIZE = 8
Q = 30
REPEAT = 3
ROW, COL = 4, 3
LUMINANCE = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def capacity_bytes(img):
    # The first two shape entries are height and width. // rounds down to whole blocks.
    height, width = img.shape[:2]
    blocks = (height // BLOCK_SIZE) * (width // BLOCK_SIZE)
    return max(0, (blocks // REPEAT - HEADER_BITS) // 8)


def block_pixels(img, offset, count):
    blocks_across = img.shape[1] // BLOCK_SIZE
    # divmod gives the row (quotient) and column (remainder) of each block number.
    block_rows, block_cols = np.divmod(np.arange(offset, offset + count), blocks_across)
    row_starts = BLOCK_SIZE * block_rows
    col_starts = BLOCK_SIZE * block_cols
    inside_block = np.arange(BLOCK_SIZE)
    # None inserts a length-one axis. Broadcasting pairs every row and column
    # within each block, so the two arrays index a (count, 8, 8) grid.
    rows = row_starts[:, None, None] + inside_block[None, :, None]
    cols = col_starts[:, None, None] + inside_block[None, None, :]
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
    first_block = offset * REPEAT
    pixels = block_pixels(img, first_block, count * REPEAT)
    brightness = img[pixels] @ LUMINANCE
    coeffs = dctn(brightness, axes=(-2, -1), norm="ortho")
    # Modulo 2 maps even indices to 0 and odd ones to 1.
    block_bits = np.rint(coeffs[:, ROW, COL] / Q).astype(int) % 2
    # -1 lets NumPy infer the number of groups. Summing across each row counts its 1s.
    votes = block_bits.reshape(-1, REPEAT).sum(axis=1)
    return votes > REPEAT // 2


def extract(img):
    capacity = capacity_bytes(img)
    if capacity == 0:
        raise ValueError(NO_MESSAGE)
    header = read_bits(img, 0, HEADER_BITS)
    length = message_length(header, capacity)
    data = read_bits(img, HEADER_BITS, 8 * length)
    return decode_message(data)
