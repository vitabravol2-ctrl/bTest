import asyncio
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.analyzer import AnalyzerConfig, DataAnalyzer
from app.config import (
    ANALYSIS_LOG_INTERVAL_MS,
    DETECTOR_LOG_INTERVAL_MS,
    FAST_WINDOW_MS,
    MAX_ALLOWED_SPREAD_PCT,
    MAX_BUFFER,
    MID_WINDOW_MS,
    MIN_TICKS_FAST,
    SLOW_WINDOW_MS,
    STALE_AFTER_MS,
    STALE_MS,
    SYMBOL,
)
from app.detector import LiquidityGrabDetector
from app.logger import setup_logging
from app.market_buffer import MarketBuffer
from app.market_ws import MarketWSClient
from app.strategy.liquidity_grab_fsm import LiquidityGrabFSM


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("bTest Cockpit — BTCUSDT Liquidity Grab")
        self.resize(1320, 860)
        self.setMinimumSize(1180, 760)

        self.buffer = MarketBuffer(maxlen=MAX_BUFFER)
        self.fsm = LiquidityGrabFSM()
        self.detector = LiquidityGrabDetector()
        self.analyzer = DataAnalyzer(
            AnalyzerConfig(FAST_WINDOW_MS, MID_WINDOW_MS, SLOW_WINDOW_MS, MIN_TICKS_FAST, STALE_AFTER_MS)
        )

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(180)
        self.log_view.setObjectName("logView")
        self.logger = setup_logging(self.append_log)
        self._last_analysis_log_ms = 0
        self._last_detector_log_ms = 0

        self.ws = MarketWSClient(self.logger)
        self.ws.tick_received.connect(self.on_tick)
        self.ws.status_changed.connect(self.on_status)
        self.ws.error.connect(self.on_error)

        self._build_ui()
        self._apply_styles()
        self.on_status("DISCONNECTED")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_age)
        self.timer.start(500)

    def _make_card(self, title: str) -> tuple[QFrame, QGridLayout]:
        card = QFrame()
        card.setObjectName("card")
        wrap = QVBoxLayout(card)
        wrap.setContentsMargins(14, 12, 14, 12)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        wrap.addWidget(title_lbl)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)
        wrap.addLayout(grid)
        return card, grid

    def _make_value_label(self, size: int = 12) -> QLabel:
        lbl = QLabel("-")
        lbl.setObjectName("value")
        lbl.setProperty("size", str(size))
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _set_badge(self, label: QLabel, text: str, status: str) -> None:
        label.setText(text)
        label.setProperty("status", status)
        label.style().unpolish(label)
        label.style().polish(label)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.lbl_title = QLabel("bTest Cockpit — BTCUSDT Liquidity Grab")
        self.lbl_title.setObjectName("appTitle")
        top.addWidget(self.lbl_title, 1)

        self.badge_ws = QLabel("DISCONNECTED")
        self.badge_quality = QLabel("WAITING")
        self.badge_phase = QLabel("NO_SETUP")
        for b in (self.badge_ws, self.badge_quality, self.badge_phase):
            b.setObjectName("badge")
            top.addWidget(b)

        self.btn_connect = QPushButton("CONNECT")
        self.btn_disconnect = QPushButton("DISCONNECT")
        self.btn_clear = QPushButton("CLEAR LOG")
        self.btn_connect.clicked.connect(lambda: asyncio.create_task(self.ws.connect()))
        self.btn_disconnect.clicked.connect(lambda: asyncio.create_task(self.ws.disconnect()))
        self.btn_clear.clicked.connect(self.log_view.clear)
        for btn in (self.btn_connect, self.btn_disconnect, self.btn_clear):
            btn.setMinimumHeight(40)
            top.addWidget(btn)

        layout.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(10)

        market_card, mg = self._make_card("MARKET")
        market_card.setMinimumWidth(360)
        self.lbl_symbol = self._make_value_label(14)
        self.lbl_symbol.setText(SYMBOL)
        self.lbl_last = self._make_value_label(30)
        self.lbl_bid = self._make_value_label(16)
        self.lbl_ask = self._make_value_label(16)
        self.lbl_spread = self._make_value_label(16)
        self.lbl_age = self._make_value_label(12)
        self.lbl_tick_rate = self._make_value_label(12)
        for i, (k, v) in enumerate(
            [
                ("Symbol", self.lbl_symbol),
                ("Last Price", self.lbl_last),
                ("Bid", self.lbl_bid),
                ("Ask", self.lbl_ask),
                ("Spread %", self.lbl_spread),
                ("Tick age", self.lbl_age),
                ("Tick rate", self.lbl_tick_rate),
            ]
        ):
            mg.addWidget(QLabel(k), i, 0)
            mg.addWidget(v, i, 1)

        radar_card, dg = self._make_card("DETECTOR RADAR")
        radar_card.setMinimumWidth(520)
        self.lbl_det_phase = self._make_value_label(22)
        self.lbl_det_score = self._make_value_label(28)
        self.lbl_det_side = self._make_value_label(14)
        self.lbl_signal = self._make_value_label(14)
        self.lbl_reason = self._make_value_label(12)
        self.lbl_reason.setWordWrap(True)
        self.lbl_reason_codes = self._make_value_label(11)
        self.lbl_reason_codes.setWordWrap(True)
        self.lbl_reason_codes.setMaximumHeight(52)
        self.lbl_setup_age = self._make_value_label(12)
        self.lbl_reclaim_hold = self._make_value_label(12)
        self.lbl_last_invalid = self._make_value_label(12)
        self.lbl_last_invalid.setWordWrap(True)
        for i, (k, v) in enumerate(
            [
                ("Phase", self.lbl_det_phase),
                ("Score", self.lbl_det_score),
                ("Side", self.lbl_det_side),
                ("Signal", self.lbl_signal),
                ("Reason", self.lbl_reason),
                ("Reason codes", self.lbl_reason_codes),
                ("Setup age", self.lbl_setup_age),
                ("Reclaim hold", self.lbl_reclaim_hold),
                ("Last invalid reason", self.lbl_last_invalid),
            ]
        ):
            dg.addWidget(QLabel(k), i, 0)
            dg.addWidget(v, i, 1)

        analyzer_card, ag = self._make_card("ANALYZER")
        analyzer_card.setMinimumWidth(360)
        self.lbl_fast_drop = self._make_value_label(16)
        self.lbl_fast_bounce = self._make_value_label(16)
        self.lbl_speed = self._make_value_label(16)
        self.lbl_volatility = self._make_value_label(16)
        self.lbl_spread_avg = self._make_value_label(16)
        self.lbl_state = self._make_value_label(14)
        for i, (k, v) in enumerate(
            [
                ("Fast drop %", self.lbl_fast_drop),
                ("Fast bounce %", self.lbl_fast_bounce),
                ("Speed %/sec", self.lbl_speed),
                ("Volatility %", self.lbl_volatility),
                ("Spread avg %", self.lbl_spread_avg),
                ("FSM state", self.lbl_state),
            ]
        ):
            ag.addWidget(QLabel(k), i, 0)
            ag.addWidget(v, i, 1)

        body.addWidget(market_card)
        body.addWidget(radar_card, 1)
        body.addWidget(analyzer_card)
        layout.addLayout(body, 1)
        layout.addWidget(self.log_view)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #0b1020; color: #dbe7ff; }
            #appTitle { font-size: 20px; font-weight: 700; color: #9ed0ff; }
            #card { background: #121a2e; border: 1px solid #1f2e4b; border-radius: 10px; }
            #cardTitle { font-size: 12px; font-weight: 700; color: #7fb1ff; letter-spacing: 0.8px; }
            QLabel { font-size: 11px; color: #93a8c8; }
            QLabel#value { color: #ecf4ff; }
            QLabel#value[size="30"] { font-size: 30px; font-weight: 700; color: #8ef2d0; }
            QLabel#value[size="28"] { font-size: 28px; font-weight: 700; color: #8ef2d0; }
            QLabel#value[size="22"] { font-size: 22px; font-weight: 700; color: #9ed0ff; }
            QLabel#value[size="16"] { font-size: 16px; font-weight: 600; }
            QLabel#value[size="14"] { font-size: 14px; font-weight: 600; }
            QLabel#value[size="12"] { font-size: 12px; }
            QLabel#value[size="11"] { font-size: 11px; }
            #badge { border-radius: 9px; padding: 5px 10px; font-size: 11px; font-weight: 700; color: #0b1020; }
            #badge[status="green"] { background: #32d296; }
            #badge[status="gray"] { background: #64748b; color: #f8fafc; }
            #badge[status="blue"] { background: #60a5fa; }
            #badge[status="orange"] { background: #fb923c; }
            #badge[status="red"] { background: #ef4444; color: #fef2f2; }
            QPushButton { background: #1e2c49; color: #e2eeff; border: 1px solid #2d4570; border-radius: 8px; padding: 8px 14px; font-size: 12px; font-weight: 700; }
            QPushButton:hover { background: #2c4067; }
            QPushButton:pressed { background: #15213a; }
            #logView { background: #0f1729; border: 1px solid #1f2e4b; border-radius: 8px; font-size: 11px; }
            """
        )

    def append_log(self, message: str) -> None:
        self.log_view.append(message)

    def on_status(self, status: str) -> None:
        status_map = {"CONNECTED": "green", "DISCONNECTED": "gray", "STALE": "orange"}
        self._set_badge(self.badge_ws, status, status_map.get(status, "gray"))

    def on_error(self, message: str) -> None:
        self.append_log(f"ERROR | {message}")

    def _quality_label(self, fast_metrics) -> str:
        if not fast_metrics.enough_data:
            return "WAITING"
        if fast_metrics.stale:
            return "STALE"
        if fast_metrics.spread_avg_pct > MAX_ALLOWED_SPREAD_PCT:
            return "BAD_SPREAD"
        return "GOOD"

    def _quality_status(self, quality: str) -> str:
        return {
            "GOOD": "green",
            "WAITING": "gray",
            "STALE": "orange",
            "BAD_SPREAD": "red",
            "HIGH_SPREAD": "orange",
        }.get(quality, "gray")

    def _phase_status(self, phase: str) -> str:
        return {
            "WATCHING_DROP": "blue",
            "LIQUIDITY_SWEEP": "orange",
            "RECLAIM_WAIT": "orange",
            "LONG_SIGNAL": "green",
            "INVALIDATED": "red",
        }.get(phase, "gray")

    def on_tick(self, tick) -> None:
        self.buffer.add_tick(tick)
        self.lbl_last.setText(f"{tick.mid:.2f}")
        self.lbl_bid.setText(f"{tick.bid:.2f}")
        self.lbl_ask.setText(f"{tick.ask:.2f}")
        self.lbl_spread.setText(f"{tick.spread_pct:.5f}")

        m = self.analyzer.analyze(self.buffer)
        fast_metrics = m["fast"]
        signal = self.detector.detect(m["fast"], m["mid"], m["slow"], self.buffer)
        result = self.fsm.evaluate(signal)

        self.lbl_fast_drop.setText(f"{fast_metrics.drop_pct:.5f}")
        self.lbl_fast_bounce.setText(f"{fast_metrics.bounce_pct:.5f}")
        self.lbl_speed.setText(f"{fast_metrics.impulse_speed_pct_per_sec:.5f}")
        self.lbl_volatility.setText(f"{fast_metrics.volatility_pct:.5f}")
        self.lbl_spread_avg.setText(f"{fast_metrics.spread_avg_pct:.5f}")
        self.lbl_tick_rate.setText(f"{fast_metrics.tick_rate:.2f} t/s")

        quality = self._quality_label(fast_metrics)
        self._set_badge(self.badge_quality, quality, self._quality_status(quality))

        self.lbl_det_phase.setText(signal.phase)
        self.lbl_det_score.setText(f"{signal.score:.2f}")
        self.lbl_det_side.setText(signal.side)
        self.lbl_reason_codes.setText(", ".join(signal.reason_codes) if signal.reason_codes else "-")
        self.lbl_reason.setText(signal.human_reason)
        self.lbl_setup_age.setText(f"{signal.setup_age_ms} ms")
        self.lbl_reclaim_hold.setText(f"{signal.reclaim_hold_ms} ms")
        self.lbl_last_invalid.setText(signal.last_invalid_reason)

        self.lbl_state.setText(result.state)
        self.lbl_signal.setText(result.signal)

        self._set_badge(self.badge_phase, signal.phase, self._phase_status(signal.phase))
        if result.signal == "LONG_SIGNAL":
            self.lbl_signal.setStyleSheet("color:#32d296;font-weight:700;")
        elif result.state == "INVALIDATED":
            self.lbl_signal.setStyleSheet("color:#ef4444;font-weight:700;")
        else:
            self.lbl_signal.setStyleSheet("")

        if tick.ts_ms - self._last_analysis_log_ms >= ANALYSIS_LOG_INTERVAL_MS:
            self._last_analysis_log_ms = tick.ts_ms
            self.logger.info(
                "Analyzer drop=%.5f bounce=%.5f speed=%.5f spread=%.5f",
                fast_metrics.drop_pct,
                fast_metrics.bounce_pct,
                fast_metrics.impulse_speed_pct_per_sec,
                fast_metrics.spread_avg_pct,
            )

        if tick.ts_ms - self._last_detector_log_ms >= DETECTOR_LOG_INTERVAL_MS:
            self._last_detector_log_ms = tick.ts_ms
            self.logger.info(
                "Detector phase=%s score=%.2f side=%s reasons=%s detected=%s",
                signal.phase,
                signal.score,
                signal.side,
                signal.reason_codes,
                signal.detected,
            )
            if "LONG_SIGNAL_READY" in signal.reason_codes:
                self.logger.warning("LIQUIDITY GRAB LONG SIGNAL READY")

    def refresh_age(self) -> None:
        now = int(time.time() * 1000)
        last = self.buffer.last()
        if not last:
            self.lbl_age.setText("-")
            return
        age = now - last.ts_ms
        stale = self.buffer.is_stale(STALE_MS, now)
        age_text = f"{age} ms"
        if stale:
            age_text += " (STALE)"
            self._set_badge(self.badge_ws, "STALE", "orange")
        self.lbl_age.setText(age_text)

    def closeEvent(self, event):  # noqa: N802
        asyncio.create_task(self.ws.disconnect())
        super().closeEvent(event)


def run_app() -> None:
    app = QApplication([])
    window = MainWindow()
    window.show()

    loop = asyncio.get_event_loop()

    async def qt_loop() -> None:
        while True:
            app.processEvents()
            await asyncio.sleep(0.01)
            if not window.isVisible():
                break

    loop.run_until_complete(qt_loop())
