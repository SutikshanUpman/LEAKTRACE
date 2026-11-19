"""Run project checks with python test_all.py."""

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

import stego_dct
import stego_lsb
import stego_text


def test_text():
    memo = stego_text.MEMO
    assert stego_text.coverage(memo) == 8
    for recipient_id in range(1, 256):
        personalised = stego_text.embed_id(memo, recipient_id)
        assert stego_text.extract_id(personalised)[0] == recipient_id
    repeated = stego_text.embed_id(f"{memo}\n{memo}", 5)
    assert stego_text.extract_id(repeated.splitlines()[1])[0] == 5
    assert stego_text.extract_id("The large launch")[0] is None
    assert stego_text.extract_id(memo + " large")[0] is None
    assert stego_text.coverage("ébig") == 0


def test_lsb():
    # A fixed seed gives this test repeatable random pixels.
    cover = np.random.default_rng(42).integers(0, 256, (32, 32, 3), dtype=np.uint8)
    message = "Launch memo: café ✓"
    stego = stego_lsb.embed(cover, message)
    assert stego_lsb.extract(stego) == message
    # Cast before subtraction to keep negative differences from wrapping in uint8.
    assert np.abs(stego.astype(int) - cover).max() == 1
    assert not np.shares_memory(cover, stego)
    assert stego_lsb.capacity_bytes(cover) == 380


def test_dct():
    cover = np.random.default_rng(42).integers(0, 256, (1025, 1027, 3), dtype=np.uint8)
    message = "Frequency-domain memo: café ✓"
    stego = stego_dct.embed(cover, message)
    assert stego_dct.extract(stego) == message
    assert stego_dct.capacity_bytes(cover) == 678
    # Negative slice indices count back from the end. These are the final row and three columns.
    assert np.array_equal(stego[-1], cover[-1])
    assert np.array_equal(stego[:, -3:], cover[:, -3:])


def test_full_chain():
    sample = Path(__file__).with_name("samples") / "blue-marble.jpg"
    with Image.open(sample) as image:
        cover = np.array(image.convert("RGB"))
    for method in (stego_lsb, stego_dct):
        for recipient_id in (1, 2, 3):
            memo = stego_text.embed_id(stego_text.MEMO, recipient_id)
            png = BytesIO()
            Image.fromarray(method.embed(cover, memo)).save(png, format="PNG")
            # Pillow accepts the in-memory PNG buffer in place of a file path.
            with Image.open(png) as image:
                recovered = method.extract(np.array(image))
            assert recovered == memo
            assert stego_text.extract_id(recovered)[0] == recipient_id


# Python sets __name__ to "__main__" when this file is run directly.
if __name__ == "__main__":
    test_text()
    test_lsb()
    test_dct()
    test_full_chain()
    print("All tests passed")
