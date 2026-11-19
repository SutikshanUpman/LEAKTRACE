"""Send or receive one LeakTrace PNG over localhost TCP."""

import argparse
from pathlib import Path
import socket

ADDRESS = ("127.0.0.1", 5000)
TIMEOUT = 10
MAX_BYTES = 10 * 1024 * 1024
LENGTH_BYTES = 4
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
METHODS = ("lsb", "dct")


def read_exact(connection, size):
    data = bytearray()
    while len(data) < size:
        # recv can return fewer bytes than requested. An empty result means EOF.
        chunk = connection.recv(min(size - len(data), 65536))
        if not chunk:
            raise ValueError("Connection closed before the transfer finished.")
        data.extend(chunk)
    return bytes(data)


def validate_png(png):
    if len(png) > MAX_BYTES or not png.startswith(PNG_SIGNATURE):
        raise ValueError("Choose a PNG file of at most 10 MiB.")


def send_png(connection, method, png):
    validate_png(png)
    method_code = METHODS.index(method)
    header = bytes([method_code]) + len(png).to_bytes(LENGTH_BYTES, "big")
    # sendall keeps writing until all bytes have been sent or an error occurs.
    connection.sendall(header)
    connection.sendall(png)


def receive_png(connection):
    header = read_exact(connection, 1 + LENGTH_BYTES)
    method_code = header[0]
    size = int.from_bytes(header[1:], "big")
    if method_code >= len(METHODS) or not len(PNG_SIGNATURE) <= size <= MAX_BYTES:
        raise ValueError("Invalid transfer header.")
    png = read_exact(connection, size)
    if not png.startswith(PNG_SIGNATURE):
        raise ValueError("Received data is missing the PNG signature.")
    return METHODS[method_code], png


def send_file(path, method):
    with path.open("rb") as source:
        png = source.read(MAX_BYTES + 1)
    # Reject an invalid local file before using the receiver's one connection.
    validate_png(png)
    with socket.create_connection(ADDRESS, timeout=TIMEOUT) as connection:
        send_png(connection, method, png)
    print(f"Sent {len(png)} bytes using {method.upper()}.")


def receive_file(path):
    if path.exists():
        raise FileExistsError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with socket.create_server(ADDRESS) as server:
        print(f"Listening on {ADDRESS[0]}:{ADDRESS[1]}", flush=True)
        connection, _ = server.accept()
        with connection:
            connection.settimeout(TIMEOUT)
            method, png = receive_png(connection)
    # Exclusive creation preserves an existing output file.
    with path.open("xb") as output:
        output.write(png)
    print(f"Saved {path}. Select {method.upper()} in the Recipient tab.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    sender = commands.add_parser("send")
    sender.add_argument("path", type=Path)
    sender.add_argument("method", choices=METHODS)
    receiver = commands.add_parser("receive")
    receiver.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "send":
            send_file(args.path, args.method)
        else:
            receive_file(args.path)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Transfer failed: {error}\n")


if __name__ == "__main__":
    main()
