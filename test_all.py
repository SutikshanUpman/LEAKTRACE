"""Run project checks with python test_all.py."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from PIL import Image

import stego_dct
import stego_lsb
import stego_text
import tcp_transfer


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


def transfer_in_test(method, png):
    sender, receiver = socket.socketpair()
    with sender, receiver, ThreadPoolExecutor(max_workers=1) as worker:
        sender.settimeout(5)
        receiver.settimeout(5)
        # Write in another thread so the receiver can read while the socket buffer fills.
        transfer = worker.submit(tcp_transfer.send_png, sender, method, png)
        result = tcp_transfer.receive_png(receiver)
        transfer.result()
    return result


def test_full_chain():
    sample = Path(__file__).with_name("samples") / "blue-marble.jpg"
    with Image.open(sample) as image:
        cover = np.array(image.convert("RGB"))
    for method_name, method in (("lsb", stego_lsb), ("dct", stego_dct)):
        for recipient_id in (1, 2, 3):
            memo = stego_text.embed_id(stego_text.MEMO, recipient_id)
            png = BytesIO()
            Image.fromarray(method.embed(cover, memo)).save(png, format="PNG")
            original = png.getvalue()
            received_method, received = transfer_in_test(method_name, original)
            assert (received_method, received) == (method_name, original)
            # Pillow accepts the in-memory PNG buffer in place of a file path.
            with Image.open(BytesIO(received)) as image:
                recovered = method.extract(np.array(image))
            assert recovered == memo
            assert stego_text.extract_id(recovered)[0] == recipient_id


def test_transfer_chunks():
    class ChunkedConnection(BytesIO):
        def recv(self, size):
            return self.read(min(size, 2))

    png = tcp_transfer.PNG_SIGNATURE
    packet = bytes([1]) + len(png).to_bytes(4, "big") + png
    assert tcp_transfer.receive_png(ChunkedConnection(packet)) == ("dct", png)
    try:
        tcp_transfer.receive_png(ChunkedConnection(packet[:-1]))
    except ValueError as error:
        assert "before the transfer finished" in str(error)
    else:
        raise AssertionError("An incomplete transfer was accepted.")


def test_transfer_file_checks():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "existing.png"
        path.write_bytes(b"example")
        with patch.object(socket, "create_connection") as connect:
            try:
                tcp_transfer.send_file(path, "dct")
            except ValueError as error:
                assert "Choose a PNG" in str(error)
            else:
                raise AssertionError("An invalid sender file was accepted.")
            connect.assert_not_called()
        with patch.object(socket, "create_server") as listen:
            try:
                tcp_transfer.receive_file(path)
            except FileExistsError:
                pass
            else:
                raise AssertionError("An existing output path was accepted.")
            listen.assert_not_called()
        assert path.read_bytes() == b"example"


# Python sets __name__ to "__main__" when this file is run directly.
if __name__ == "__main__":
    test_text()
    test_lsb()
    test_dct()
    test_full_chain()
    test_transfer_chunks()
    test_transfer_file_checks()
    print("All tests passed")
