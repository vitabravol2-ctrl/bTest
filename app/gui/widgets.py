from PySide6.QtWidgets import QLabel


def kv_label(name: str, value: str = "-") -> tuple[QLabel, QLabel]:
    k = QLabel(name)
    v = QLabel(value)
    v.setStyleSheet("font-weight: 600;")
    return k, v
