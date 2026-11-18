"""Hide UTF-8 text in the least significant bits of an RGB image."""

import numpy as np

HEADER_BITS = 32
NO_MESSAGE = "No valid hidden message found. Check the image and method."


def capacity_bytes(img):
    return max(0, (img.size - HEADER_BITS) // 8)


def pack_message(text, capacity):
    data = text.encode("utf-8")
    if not data:
        raise ValueError("Enter a message first.")
    if len(data) > capacity:
        raise ValueError(f"Message uses {len(data)} bytes, but this image holds {capacity}.")
    payload = len(data).to_bytes(4, "big") + data
    return np.unpackbits(np.frombuffer(payload, dtype=np.uint8))


def message_length(header, capacity):
    length = int.from_bytes(np.packbits(header).tobytes(), "big")
    if header.size != HEADER_BITS or not 0 < length <= capacity:
        raise ValueError(NO_MESSAGE)
    return length


def decode_message(bits):
    try:
        return np.packbits(bits).tobytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(NO_MESSAGE) from error


def embed(img, text):
    bits = pack_message(text, capacity_bytes(img))
    flat = img.flatten()
    flat[:bits.size] = (flat[:bits.size] & 0xFE) | bits
    return flat.reshape(img.shape)


def extract(img):
    flat = img.ravel()
    length = message_length(flat[:HEADER_BITS] & 1, capacity_bytes(img))
    return decode_message(flat[HEADER_BITS:HEADER_BITS + 8 * length] & 1)
