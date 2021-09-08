import math
import sys

import trio
import trio.socket as socket

from traceroute import net


iteration: int = 0


async def tracer(
    mem_channel: trio.MemorySendChannel,
    mutex: trio.Lock,
    send_sock: socket.SocketType,
    recv_sock: socket.SocketType,
    dest: str
) -> None:
    async with mem_channel, mutex:
        global iteration
        iteration += 1

        net.set_ttl(send_sock, ttl=iteration)
        packet = net.build_icmp_packet(seq_no=iteration)

        await send_sock.sendto(packet, (dest, 33434))
        _, addr = await recv_sock.recvfrom(1024)

        await mem_channel.send((iteration, addr[0]))


async def printer(
    mem_channel: trio.MemoryReceiveChannel,
    cancel_scope: trio.CancelScope,
    dest: str
) -> None:
    async with mem_channel:
        async for (iteration, addr) in mem_channel:
            print('%d: %s' % (iteration, addr))
            if addr == dest:
                await cancel_scope.cancel()


async def main(proto: net.Protocol, dest: str, max_probes: int = 30) -> None:
    mutex = trio.Lock()
    send_sock, recv_sock = net.create_sock_pair(proto)
    with send_sock, recv_sock:
        async with trio.open_nursery() as nursery:
            tx, rx = trio.open_memory_channel(math.inf)
            nursery.start_soon(printer, rx, nursery.cancel_scope, dest)
            for _ in range(1, max_probes + 1):
                nursery.start_soon(
                    tracer,
                    tx.clone(),
                    mutex,
                    send_sock,
                    recv_sock,
                    dest
                )


if __name__ == '__main__':
    proto = net.Protocol.from_str(sys.argv[1])
    trio.run(main, proto, '172.217.169.174')
