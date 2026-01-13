import socket


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_external_address(sock: socket.socket):
    try:
        tmp = socket.socket(socket.AF_INET, socket.SGRAM)
        try:
            tmp.connect(("8.8.8.8", 80))
            ip = tmp.getsockname()[0]
        finally:
            tmp.close()

        _, port = sock.getsockname()
        return ip, port
    except Exception:
        return None
