import time
from typing import List, Tuple, Set, Dict


class DHT:
    def __init__(self):
        self.peers: Set[Tuple[str, int]] = set()
        self.last_seen: Dict[Tuple[str, int], float] = {}

    def add_peer(self, addr: Tuple[str, int]) -> None:
        self.peers.add(addr)
        self.last_seen[addr] = time.time()

    def remove_peer(self, addr: Tuple[str, int]) -> None:
        self.peers.discard(addr)
        self.last_seen.pop(addr, None)

    def get_peers(self) -> List[Tuple[str, int]]:
        return sorted(self.peers)

    def mark_seen(self, addr: Tuple[str, int]) -> None:
        self.last_seen[addr] = time.time()

    def cleanup(self, timeout: float) -> None:
        now = time.time()
        to_remove = []

        for peer in list(self.peers):
            ts = self.last_seen.get(peer)
            if ts is None:
                continue
            if now - ts > timeout:
                to_remove.append(peer)

        for peer in to_remove:
            self.remove_peer(peer)
