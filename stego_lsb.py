"""Hide UTF-8 text in the least significant bits of an RGB image."""

import numpy as np

# The payload starts with the memo length, followed by the UTF-8 memo bytes.
# For "A", the five bytes in hex are 00 00 00 01 41.
HEADER_BYTES = 4
HEADER_BITS = 8 * HEADER_BYTES
NO_MESSAGE = "No valid hidden message found. Check the image and method."


def capacity_bytes(img):
    # img.size counts individual RGB channels. Each channel can carry one bit.
    # Reserve the header bits, then use // 8 to count only whole memo bytes.
    return max(0, (img.size - HEADER_BITS) // 8)


def pack_message(text, capacity):
    # Capacity is measured in bytes. A character like é can use multiple bytes.
    data = text.encode("utf-8")
    if not data:
        raise ValueError("Enter a message first.")
    if len(data) > capacity:
        raise ValueError(f"Message uses {len(data)} bytes, but this image holds {capacity}.")
    # to_bytes stores the byte count in four bytes, most significant byte first.
    payload = len(data).to_bytes(HEADER_BYTES, "big") + data
    # frombuffer reads the bytes as uint8 values. unpackbits expands each into eight bits.
    return np.unpackbits(np.frombuffer(payload, dtype=np.uint8))


def message_length(header, capacity):
    # packbits and from_bytes reverse the bit expansion and integer encoding above.
    length = int.from_bytes(np.packbits(header).tobytes(), "big")
    # Reject an incomplete header or a length that cannot fit before reading the memo.
    # Python chains the comparisons, so this checks both bounds on length.
    if header.size != HEADER_BITS or not 0 < length <= capacity:
        raise ValueError(NO_MESSAGE)
    return length


def decode_message(bits):
    try:
        return np.packbits(bits).tobytes().decode("utf-8")
    except UnicodeDecodeError as error:
        # "raise ... from" keeps the original error attached as the cause.
        raise ValueError(NO_MESSAGE) from error


def embed(img, text):
    bits = pack_message(text, capacity_bytes(img))
    # flatten copies the image into a 1D array in R, G, B order for each pixel.
    flat = img.flatten()
    # This slice is a view, so writing to channels[:] updates flat.
    channels = flat[:bits.size]
    # 0xFE is 11111110 in binary. AND clears each lowest bit, and OR writes
    # the corresponding payload bit. A channel value of 200 becomes 201 for a 1.
    channels[:] = (channels & 0xFE) | bits
    return flat.reshape(img.shape)


def extract(img):
    # ravel reads channels in the same order as flatten. & 1 keeps only the lowest bit.
    flat = img.ravel()
    header = flat[:HEADER_BITS] & 1
    length = message_length(header, capacity_bytes(img))
    # Each memo byte takes eight channels. A one-byte memo uses flat[32:40].
    end = HEADER_BITS + 8 * length
    data = flat[HEADER_BITS:end] & 1
    return decode_message(data)
