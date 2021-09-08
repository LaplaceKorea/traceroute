import ctypes
import enum
import struct
import trio.socket as socket
import typing as t


ICMP_ECHO_REQUEST_TYPE = 0x8
ICMP_ECHO_REQUEST_CODE = 0x0
ICMP_ECHO_REQUEST_ID = 0x1

SockPair: t.TypeAlias = t.Tuple[socket.SocketType, socket.SocketType]


class Protocol(enum.Enum):
    UDP = enum.auto()
    ICMP = enum.auto()

    @classmethod
    def from_str(cls, string: str) -> 'Protocol':
        match string.upper():
            case "UDP":
                return cls.UDP
            case "ICMP":
                return cls.ICMP
            case _:
                raise ValueError('Not implemented.')


def create_sock_pair(proto: Protocol) -> SockPair:
    match proto:
        case Protocol.ICMP:
            send_sock = recv_sock = _create_icmp_sock()
            return (send_sock, recv_sock)
        case Protocol.UDP:
            send_sock = _create_udp_sock()
            recv_sock = _create_icmp_sock()
            return (send_sock, recv_sock)


def _create_icmp_sock() -> socket.SocketType:
    """
    Creates a raw Internet socket that speaks ICMP.
    """
    return socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)


def _create_udp_sock() -> socket.SocketType:
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)


def set_ttl(sock: socket.SocketType, ttl: int) -> None:
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)


def build_icmp_packet(seq_no: int) -> bytes:
    """
    Builds a 64-bit (8-byte) ICMP echo request header.
    The fields are [numbers are in bits]:

    TYPE (8), CODE (8), CHECKSUM (16), ID (16), SEQ_NO (16)
    """
    size = struct.calcsize('!BBHHH')
    assert size == 8  # in bytes

    buf = ctypes.create_string_buffer(size)

    struct.pack_into(
        '!BBHHH',
        buf,
        0,
        ICMP_ECHO_REQUEST_TYPE,
        ICMP_ECHO_REQUEST_CODE,
        0x0,  # checksum
        ICMP_ECHO_REQUEST_ID,
        seq_no
    )

    struct.pack_into('!H', buf, 2, _internet_checksum(bytes(buf)))

    return bytes(buf)


def _internet_checksum(header: bytes) -> int:
    """
    Sums up 16-bit sequences and
    takes one's complement of the result.
    Finally, low-end 16-bits are returned.
    """
    checksum = 0

    for idx in range(0, len(header), 2):
        checksum += (header[idx] << 8) | header[idx + 1]

    checksum = ~checksum & 0xffff
    assert checksum.bit_length() == 16

    return checksum
