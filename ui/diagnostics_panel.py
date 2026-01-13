from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt, QMetaObject, Q_ARG, Signal


class DiagnosticsPanel(QWidget):
    # сигналы для безопасного обновления из других потоков
    status_update_requested = Signal(str, str, bool, int)
    dht_update_requested = Signal(list)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Диагностическая панель")

        layout = QVBoxLayout(self)

        # Логи
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(QLabel("Логи (реальное время):"))
        layout.addWidget(self.log_view)

        # Кнопки
        self.btn_clear = QPushButton("Очистить лог")
        self.btn_save = QPushButton("Сохранить лог")
        self.btn_refresh = QPushButton("Обновить статус")

        layout.addWidget(self.btn_clear)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_refresh)

        # DHT таблица
        layout.addWidget(QLabel("DHT-соседи:"))
        self.dht_table = QTableWidget(0, 3)
        self.dht_table.setHorizontalHeaderLabels(["IP", "Port", "Last seen"])
        self.dht_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.dht_table)

        # Статус сети
        layout.addWidget(QLabel("Сетевой статус:"))
        self.label_local_ip = QLabel("Локальный IP: -")
        self.label_zt_ip = QLabel("ZeroTier IP: -")
        self.label_udp = QLabel("UDP доступность: -")
        self.label_port = QLabel("Порт: -")

        layout.addWidget(self.label_local_ip)
        layout.addWidget(self.label_zt_ip)
        layout.addWidget(self.label_udp)
        layout.addWidget(self.label_port)

        # Кнопки
        self.btn_clear.clicked.connect(self.clear_log)

        # сигналы → слоты
        self.status_update_requested.connect(self._update_status)
        self.dht_update_requested.connect(self._update_dht)

    # ---------------- ЛОГИ ----------------

    def add_log(self, text: str):
        # append — настоящий Qt-слот, безопасно вызывать через invokeMethod
        QMetaObject.invokeMethod(
            self.log_view,
            "append",
            Qt.QueuedConnection,
            Q_ARG(str, text),
        )

    def clear_log(self):
        self.log_view.clear()

    # ---------------- СЕТЕВОЙ СТАТУС ----------------

    def safe_update_status(self, local_ip, zt_ip, udp_ok, port):
        # главное: никаких invokeMethod здесь
        self.status_update_requested.emit(str(local_ip), str(zt_ip), bool(udp_ok), int(port))

    def _update_status(self, local_ip, zt_ip, udp_ok, port):
        self.label_local_ip.setText(f"Локальный IP: {local_ip}")
        self.label_zt_ip.setText(f"ZeroTier IP: {zt_ip}")
        self.label_udp.setText(f"UDP доступность: {'да' if udp_ok else 'нет'}")
        self.label_port.setText(f"Порт: {port}")

    # ---------------- DHT ----------------

    def safe_update_dht(self, peers):
        # peers — список (ip, port, last_seen_str)
        self.dht_update_requested.emit(list(peers))

    def _update_dht(self, peers):
        self.dht_table.setRowCount(0)

        for ip, port, last_seen in peers:
            row = self.dht_table.rowCount()
            self.dht_table.insertRow(row)
            self.dht_table.setItem(row, 0, QTableWidgetItem(str(ip)))
            self.dht_table.setItem(row, 1, QTableWidgetItem(str(port)))
            self.dht_table.setItem(row, 2, QTableWidgetItem(str(last_seen)))
