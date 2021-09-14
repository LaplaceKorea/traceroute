import argparse
import math

import trio

from traceroute import core, net

parser = argparse.ArgumentParser()
parser.add_argument('--dest', required=True)
parser.add_argument('--proto', default='UDP')

async def main(proto: net.Protocol, dest: str, max_probes: int = 30) -> None:
    mutex = trio.Lock()
    send_sock, recv_sock = net.create_sock_pair(proto)
    with send_sock, recv_sock:
        async with trio.open_nursery() as nursery:
            tx, rx = trio.open_memory_channel(math.inf)
            nursery.start_soon(core.printer, rx, nursery.cancel_scope, dest)
            for _ in range(1, max_probes + 1):
                nursery.start_soon(
                    core.tracer,
                    tx.clone(),
                    mutex,
                    send_sock,
                    recv_sock,
                    dest
                )


if __name__ == '__main__':
    args = parser.parse_args()
    proto = net.Protocol.from_str(args.proto)
    trio.run(main, proto, args.dest)
