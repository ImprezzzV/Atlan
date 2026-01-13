import json
from enum import Enum


class PacketType(Enum):
    HELLO = "HELLO"
    MESSAGE = "MESSAGE"
    NODE_LIST = "NODE_LIST"
    PING = "PING"


def encode_packet(packet: dict) -> bytes:
    return json.dumps(packet).encode("utf-8")


def decode_packet(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))
