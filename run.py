from core.nat_traversal import get_local_ip
from core.node import Node
from PySide6.QtWidgets import QApplication
from ui.diagnostics_panel import DiagnosticsPanel
from core.transport import Logger
import sys
import traceback
import requests 
import sys 
import subprocess 
import time 
import os

APP_VERSION = "1.0.0"
UPDATE_URL = "https://github.com/ImprezzzV/Atlan.git"

def check_for_updates():
    try:
        r = requests.get(UPDATE_URL, timeout=3)
        data = r.json()
        latest = data["version"]

        if latest != APP_VERSION:
            print("Доступна новая версия:", latest)
            download_url = data["url"]

            subprocess.Popen([
                "updater.exe",
                download_url,
                sys.argv[0]
            ])
            sys.exit(0)

    except Exception as e:
        print("Ошибка проверки обновлений:", e)



def excepthook(type, value, tb):
    print("\n=== НЕПЕРЕХВАЧЕННАЯ ОШИБКА ===")
    traceback.print_exception(type, value, tb)
    print("=== КОНЕЦ ОШИБКИ ===\n")


sys.excepthook = excepthook


def main(panel):
    check_for_updates()
    try:
        port = int(input("Введите порт узла: "))
    except Exception:
        print("Некорректный порт")
        return

    host = get_local_ip()

    node = Node(host, port, panel=panel)
    Logger.panel = panel

    node.start()

    panel.btn_refresh.clicked.connect(lambda: node.transport.update_panel_status())
    panel.btn_refresh.clicked.connect(lambda: node.update_panel_dht())

    node.transport.update_panel_status()
    node.update_panel_dht()

    print("  connect ip         - попытаться подключиться к узлу")
    print("  trace ip port      - проверить доступность узла")
    print("  watch              - мониторинг сети")
    print("  peers              - список известных пиров")
    print("  info               - информация об узле")
    print("  exit               - выход")

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        parts = cmd.split()

        if parts[0] == "exit":
            break

        elif parts[0] == "hello" and len(parts) == 3:
            ip = parts[1]
            port = int(parts[2])
            node.send_hello((ip, port))

        elif parts[0] == "msg" and len(parts) >= 4:
            ip = parts[1]
            port = int(parts[2])
            text = " ".join(parts[3:])
            node.send_message((ip, port), text)

        elif cmd == "peers":
            print("Известные пиры:")
            for p in node.dht.get_peers():
                print("  ", p)

        elif cmd == "info":
            print("Локальный адрес:", node.host, node.port)
            print("Внешний адрес:", node.external_addr)
            print("Пиров в DHT:", len(node.dht.get_peers()))

        elif parts[0] == "connect" and len(parts) == 2:
            ip = parts[1]
            node.connect(ip)

        elif parts[0] == "trace" and len(parts) == 3:
            ip = parts[1]
            port = int(parts[2])
            node.trace(ip, port)  # если у тебя нет trace, временно закомментируй эту строку

        elif parts[0] == "watch":
            node.watch()  # если нет watch, тоже закомментируй

        else:
            print("Неизвестная команда")

    print("Остановка узла...")
    node.stop()


if __name__ == "__main__":
    app = QApplication([])

    panel = DiagnosticsPanel()
    panel.show()

    Logger.panel = panel
    Logger.ui("=== ТЕСТОВАЯ ЗАПИСЬ В ЛОГ ===")

    try:
        main(panel)
    finally:
        sys.exit(0)
