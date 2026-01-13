import threading
import time
import logging
from typing import Tuple

from .transport import Transport, Logger
from .protocol import PacketType, encode_packet, decode_packet
from .dht import DHT
from .nat_traversal import get_external_address


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

HEARTBEAT_INTERVAL = 5


class Node:
    def __init__(self, host: str, port: int, panel=None):
        self.host = host
        self.port = port
        self.panel = panel

        self.dht = DHT()
        self.transport = Transport(host, port, self._safe_on_packet, panel=panel)

        self.running = False
        self.external_addr = None

    # ============================================================
    #   SAFE WRAPPER
    # ============================================================
    def _safe_on_packet(self, data, addr):
        try:
            self._on_packet(data, addr)
        except Exception as e:
            logging.error("Фатальная ошибка в обработке пакета: %s", e)

    # ============================================================
    #   START / STOP
    # ============================================================
    def start(self):
        self.running = True
        logging.info("Узел запущен на %s:%s", self.host, self.port)

        self.external_addr = get_external_address(self.transport.socket)
        logging.info("Внешний адрес узла: %s", self.external_addr)

        self.transport.start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.transport.stop()

    # ============================================================
    #   HEARTBEAT
    # ============================================================
    def _heartbeat_loop(self):
        while self.running:
            time.sleep(HEARTBEAT_INTERVAL)

            for addr in self.dht.get_peers():
                self.send_ping(addr)

            self.dht.cleanup(timeout=30)

            if self.panel:
                self.update_panel_dht()

    # ============================================================
    #   PACKET HANDLING
    # ============================================================
    def _on_packet(self, data: bytes, addr: Tuple[str, int]):

        # короткие пакеты → heartbeat
        if len(data) <= 4:
            if data.strip().upper() == b"PING":
                self.dht.mark_seen(addr)
                return

        # JSON
        try:
            packet = decode_packet(data)
        except Exception:
            logging.warning("Некорректный JSON от %s", addr)
            return

        ptype = packet.get("type")

        if ptype == PacketType.HELLO.value:
            self._handle_hello(packet, addr)

        elif ptype == PacketType.MESSAGE.value:
            self._handle_message(packet, addr)

        elif ptype == PacketType.NODE_LIST.value:
            self._handle_node_list(packet, addr)

        elif ptype == PacketType.PING.value:
            pass

        else:
            logging.warning("Неизвестный тип пакета: %s", ptype)

    # ============================================================
    #   HELLO
    # ============================================================
    def _handle_hello(self, packet, addr):
        external = packet.get("external")
        local = packet.get("local")

        # внешний адрес
        if isinstance(external, (list, tuple)) and len(external) == 2:
            try:
                ext_addr = (external[0], int(external[1]))
                if ext_addr != (self.host, self.port):
                    self.dht.add_peer(ext_addr)
            except Exception:
                pass

        # локальный адрес
        if isinstance(local, (list, tuple)) and len(local) == 2:
            try:
                loc_addr = (local[0], int(local[1]))
                if loc_addr != (self.host, self.port):
                    self.dht.add_peer(loc_addr)
            except Exception:
                pass

        # адрес отправителя
        if addr != (self.host, self.port):
            self.dht.add_peer(addr)

        self.send_node_list(addr)

    # ============================================================
    #   MESSAGE
    # ============================================================
    def _handle_message(self, packet, addr):
        text = packet.get("text", "")
        logging.info("Сообщение от %s: %s", addr, text)

    # ============================================================
    #   NODE_LIST
    # ============================================================
    def _handle_node_list(self, packet, addr):
        peers = packet.get("peers", [])

        for item in peers:
            try:
                ip, port = item
                port = int(port)
                peer_addr = (ip, port)
            except Exception:
                logging.warning("Некорректный peer в NODE_LIST: %s", item)
                continue

            if peer_addr == (self.host, self.port):
                continue

            if peer_addr not in self.dht.peers:
                self.dht.add_peer(peer_addr)
                self.send_hello(peer_addr)

        if addr != (self.host, self.port):
            self.dht.add_peer(addr)

    # ============================================================
    #   SEND
    # ============================================================
    def send_hello(self, addr):
        packet = {
            "type": PacketType.HELLO.value,
            "external": self.external_addr,
            "local": (self.host, self.port)
        }
        self.transport.send(encode_packet(packet), addr)

    def send_message(self, addr, text):
        packet = {"type": PacketType.MESSAGE.value, "text": text}
        self.transport.send(encode_packet(packet), addr)

    def send_node_list(self, addr):
        peers = [p for p in self.dht.get_peers() if p != addr]
        packet = {
            "type": PacketType.NODE_LIST.value,
            "peers": peers,
            "external": self.external_addr,
            "local": (self.host, self.port)
        }
        self.transport.send(encode_packet(packet), addr)

    def send_ping(self, addr):
        packet = {"type": PacketType.PING.value}
        self.transport.send(encode_packet(packet), addr)

    # ============================================================
    #   CONNECT
    # ============================================================
    def connect(self, ip: str):
        try:
            if ":" in ip:
                ip_addr, port = ip.split(":")
                port = int(port)
            else:
                ip_addr = ip
                port = 5000
        except Exception:
            logging.error("CONNECT: некорректный адрес %s", ip)
            return False

        self.send_hello((ip_addr, port))
        return True

    # ============================================================
    #   PANEL
    # ============================================================
    def get_dht_peers(self):
        now = time.time()
        result = []

        for peer in self.dht.get_peers():
            if not isinstance(peer, tuple) or len(peer) != 2:
                continue

            ip, port = peer
            if not isinstance(ip, str):
                continue
            if not isinstance(port, int):
                continue

            last_seen = self.dht.last_seen.get(peer)
            age = "нет данных" if last_seen is None else f"{int(now - last_seen)} сек назад"

            result.append((ip, port, age))

        return result

    def update_panel_dht(self):
        if not self.panel:
            return
        peers = self.get_dht_peers()
        self.panel.safe_update_dht(peers)

    def trace(self, ip, port):
        logging.info(f"TRACE: функция пока не реализована ({ip}:{port})")

    def watch(self):
        logging.info("WATCH: функция пока не реализована")

