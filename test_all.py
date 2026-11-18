"""Run project checks with python test_all.py."""

import numpy as np

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


def test_lsb():
    cover = np.random.default_rng(42).integers(0, 256, (32, 32, 3), dtype=np.uint8)
    message = "Launch memo: café ✓"
    stego = stego_lsb.embed(cover, message)
    assert stego_lsb.extract(stego) == message
    assert np.abs(stego.astype(int) - cover).max() == 1
    assert not np.shares_memory(cover, stego)
    assert stego_lsb.capacity_bytes(cover) == 380


def test_dct():
    cover = np.random.default_rng(42).integers(0, 256, (1025, 1027, 3), dtype=np.uint8)
    message = "Frequency-domain memo: café ✓"
    stego = stego_dct.embed(cover, message)
    assert stego_dct.extract(stego) == message
    assert stego_dct.capacity_bytes(cover) == 678
    assert np.array_equal(stego[-1], cover[-1])
    assert np.array_equal(stego[:, -3:], cover[:, -3:])


if __name__ == "__main__":
    test_text()
    test_lsb()
    test_dct()
    print("All tests passed")
