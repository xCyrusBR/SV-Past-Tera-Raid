from __future__ import annotations

import argparse
import json
import selectors
import socket
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Proxy UDP local com captura em JSONL.")
    parser.add_argument("--listen", type=int, default=24873)
    parser.add_argument("--server-port", type=int, default=24872)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind(("127.0.0.1", args.listen))
    server_address = ("127.0.0.1", args.server_port)
    server_sockets: dict[tuple[str, int], socket.socket] = {}

    selector = selectors.DefaultSelector()
    selector.register(client_socket, selectors.EVENT_READ, "client_to_server")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("a", encoding="utf-8", buffering=1) as capture:
        print(f"LISTENING 127.0.0.1:{args.listen} -> 127.0.0.1:{args.server_port}", flush=True)
        while True:
            for key, _ in selector.select():
                data, address = key.fileobj.recvfrom(65535)
                direction = key.data
                if direction == "client_to_server":
                    server_socket = server_sockets.get(address)
                    if server_socket is None:
                        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        server_socket.bind(("127.0.0.1", 0))
                        server_sockets[address] = server_socket
                        selector.register(
                            server_socket,
                            selectors.EVENT_READ,
                            ("server_to_client", address),
                        )
                    server_socket.sendto(data, server_address)
                    capture_client = address
                else:
                    direction, capture_client = direction
                    client_socket.sendto(data, capture_client)
                capture.write(
                    json.dumps(
                        {
                            "time_ns": time.time_ns(),
                            "direction": direction,
                            "source": f"{address[0]}:{address[1]}",
                            "client": f"{capture_client[0]}:{capture_client[1]}",
                            "length": len(data),
                            "hex": data.hex(),
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )


if __name__ == "__main__":
    raise SystemExit(main())
