"""Hide UTF-8 text in the least significant bits of an RGB image."""

import numpy as np

# Payload mein pehle memo ki length hoti hai, phir memo ke UTF-8 bytes.
# "A" ke liye hex mein ye paanch bytes hain: 00 00 00 01 41.
HEADER_BYTES = 4
HEADER_BITS = 8 * HEADER_BYTES
NO_MESSAGE = "No valid hidden message found. Check the image and method."


def capacity_bytes(img):
    # img.size har RGB channel value ko count karta hai. Har value mein ek bit store hoti hai.
    # Header ke bits hatao, phir // 8 se dekho kitne poore memo bytes fit honge.
    return max(0, (img.size - HEADER_BITS) // 8)


def pack_message(text, capacity):
    # Capacity bytes mein hai. é jaise ek character ko bhi kai bytes lag sakte hain.
    data = text.encode("utf-8")
    if not data:
        raise ValueError("Enter a message first.")
    if len(data) > capacity:
        raise ValueError(f"Message uses {len(data)} bytes, but this image holds {capacity}.")
    # to_bytes length ko chaar bytes mein rakhta hai, sabse significant byte pehle.
    payload = len(data).to_bytes(HEADER_BYTES, "big") + data
    # frombuffer bytes ko uint8 values ki tarah padhta hai. unpackbits har byte ke 8 bits nikalta hai.
    return np.unpackbits(np.frombuffer(payload, dtype=np.uint8))


def message_length(header, capacity):
    # packbits bits ko wapas bytes mein jodta hai. from_bytes unse length nikalta hai.
    length = int.from_bytes(np.packbits(header).tobytes(), "big")
    # Memo padhne se pehle header ka size aur length ki range check karo.
    # 0 < length <= capacity ek saath length ki dono limits check karta hai.
    if header.size != HEADER_BITS or not 0 < length <= capacity:
        raise ValueError(NO_MESSAGE)
    return length


def decode_message(bits):
    try:
        return np.packbits(bits).tobytes().decode("utf-8")
    except UnicodeDecodeError as error:
        # "raise ... from" original error ko naye error ka cause banaye rakhta hai.
        raise ValueError(NO_MESSAGE) from error


def embed(img, text):
    bits = pack_message(text, capacity_bytes(img))
    # flatten image ki 1D copy banata hai. Har pixel ke channels R, G, B order mein aate hain.
    flat = img.flatten()
    # Ye slice ek view hai, isliye channels[:] mein likhne se flat bhi update hota hai.
    channels = flat[:bits.size]
    # 0xFE binary mein 11111110 hai. AND last bit ko 0 karta hai, phir OR payload bit likhta hai.
    # Jaise, agar channel value 200 hai aur payload bit 1 hai, toh value 201 ho jaati hai.
    channels[:] = (channels & 0xFE) | bits
    return flat.reshape(img.shape)


def extract(img):
    # ravel channels ko flatten wale order mein padhta hai. & 1 sirf last bit nikalta hai.
    flat = img.ravel()
    header = flat[:HEADER_BITS] & 1
    length = message_length(header, capacity_bytes(img))
    # Memo ke har byte ke liye 8 channels chahiye. Ek byte ka memo flat[32:40] se milta hai.
    end = HEADER_BITS + 8 * length
    data = flat[HEADER_BITS:end] & 1
    return decode_message(data)
