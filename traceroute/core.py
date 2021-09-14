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