import socket
import threading
import logging
import datetime


class Logger:
    panel = None

    @staticmethod
    def _ts():
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def send(packet_type, size, ip, port):
        msg = f"[SEND] {Logger._ts()} | {packet_type} | {size} bytes | to {ip}:{port}"
        print(msg)
        Logger.ui(msg)

    @staticmethod
    def recv(packet_type, size, ip, port):
        msg = f"[RECV] {Logger._ts()} | {packet_type} | {size} bytes | from {ip}:{port}"
        print(msg)
        Logger.ui(msg)

    @staticmethod
    def error(msg):
        full = f"[ERROR] {Logger._ts()} | {msg}"
        print(full)
        Logger.ui(full)

    @staticmethod
    def route(msg):
        full = f"[ROUTE] {Logger._ts()} | {msg}"
        print(full)
        Logger.ui(full)

    @staticmethod
    def dht(msg):
        full = f"[DHT] {Logger._ts()} | {msg}"
        print(full)
        Logger.ui(full)

    @staticmethod
    def ui(text):
        if Logger.panel:
            Logger.panel.add_log(text)


class Transport:
    def __init__(self, host: str, port: int, on_packet_callback, panel=None):
        self.panel = panel
        self.host = host
        self.port = port
        self.on_packet = on_packet_callback

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", port))

        self.running = False

    # ---------------- СЕТЕВОЙ СТАТУС ----------------

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "неизвестно"

    def get_zerotier_ip(self):
        try:
            import psutil
            for iface, addrs in psutil.net_if_addrs().items():
                if iface.startswith("zt"):
                    for a in addrs:
                        if a.family == socket.AF_INET:
                            return a.address
            return "не найден"
        except Exception:
            return "неизвестно"

    def check_udp(self):
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.settimeout(0.2)
            test_sock.sendto(b"PING", ("127.0.0.1", self.port))
            test_sock.close()
            return True
        except Exception:
            return False

    def update_panel_status(self):
        if not self.panel:
            return

        local_ip = self.get_local_ip()
        zt_ip = self.get_zerotier_ip()
        udp_ok = self.check_udp()
        port = self.port

        self.panel.safe_update_status(local_ip, zt_ip, udp_ok, port)

    # ---------------- ЖИЗНЕННЫЙ ЦИКЛ ----------------

    def start(self):
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()
        logging.info("Транспорт запущен на %s:%s", self.host, self.port)

    def stop(self):
        self.running = False
        try:
            self.socket.close()
        except Exception:
            pass
        logging.info("Транспорт остановлен")

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                Logger.recv("RAW", len(data), addr[0], addr[1])

                try:
                    self.on_packet(data, addr)
                except Exception as handler_err:
                    logging.error("Ошибка в обработчике пакета: %s", handler_err)

            except Exception as e:
                msg = str(e)
                if "10054" in msg or getattr(e, "winerror", None) == 10054:
                    continue
                if "10038" in msg or getattr(e, "winerror", None) == 10038:
                    continue

                logging.error("Ошибка в listen_loop: %s", e)

    def send(self, data, addr):
        try:
            Logger.send("RAW", len(data), addr[0], addr[1])
            self.socket.sendto(data, addr)
        except Exception as e:
            logging.error("Ошибка отправки пакета: %s", e)
