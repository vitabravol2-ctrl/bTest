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
    QProgressBar,
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
        self.resize(1320, 820)
        self.setMinimumSize(1180, 720)

        self.buffer = MarketBuffer(maxlen=MAX_BUFFER)
        self.fsm = LiquidityGrabFSM()
        self.detector = LiquidityGrabDetector()
        self.analyzer = DataAnalyzer(
            AnalyzerConfig(FAST_WINDOW_MS, MID_WINDOW_MS, SLOW_WINDOW_MS, MIN_TICKS_FAST, STALE_AFTER_MS)
        )

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(130)
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
        wrap.setContentsMargins(12, 10, 12, 10)
        wrap.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        wrap.addWidget(title_lbl)
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        wrap.addLayout(grid)
        return card, grid

    def _make_value_label(self, size: int = 12, align: Qt.AlignmentFlag | None = None) -> QLabel:
        lbl = QLabel("-")
        lbl.setObjectName("value")
        lbl.setProperty("size", str(size))
        lbl.setAlignment((align or Qt.AlignmentFlag.AlignRight) | Qt.AlignmentFlag.AlignVCenter)
        return lbl

    def _create_led(self, label_text: str, initial_status: str = "off") -> tuple[QFrame, QFrame]:
        row = QFrame()
        row.setObjectName("ledRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        lamp = QFrame()
        lamp.setObjectName("ledLamp")
        lamp.setProperty("status", initial_status)
        lamp.setFixedSize(16, 16)
        name = QLabel(label_text)
        name.setObjectName("ledLabel")
        row_layout.addWidget(lamp)
        row_layout.addWidget(name)
        row_layout.addStretch(1)
        return row, lamp

    def _set_led(self, led: QFrame, status: str) -> None:
        led.setProperty("status", status)
        led.style().unpolish(led)
        led.style().polish(led)

    def _set_badge(self, label: QLabel, text: str, status: str) -> None:
        label.setText(text)
        label.setProperty("status", status)
        label.style().unpolish(label)
        label.style().polish(label)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self.lbl_title = QLabel("bTest Cockpit — BTCUSDT Liquidity Grab")
        self.lbl_title.setObjectName("appTitle")
        top.addWidget(self.lbl_title)

        self.row_ws, self.led_ws = self._create_led("WS")
        self.row_data, self.led_data = self._create_led("DATA")
        self.row_drop, self.led_drop = self._create_led("DROP")
        self.row_sweep, self.led_sweep = self._create_led("SWEEP")
        self.row_reclaim, self.led_reclaim = self._create_led("RECLAIM")
        self.row_signal, self.led_signal = self._create_led("SIGNAL")
        self.row_block, self.led_block = self._create_led("BLOCK")

        for row in (
            self.row_ws,
            self.row_data,
            self.row_drop,
            self.row_sweep,
            self.row_reclaim,
            self.row_signal,
            self.row_block,
        ):
            top.addWidget(row)

        top.addStretch(1)

        self.btn_connect = QPushButton("CONNECT")
        self.btn_disconnect = QPushButton("DISCONNECT")
        self.btn_clear = QPushButton("CLEAR LOG")
        self.btn_connect.clicked.connect(lambda: asyncio.create_task(self.ws.connect()))
        self.btn_disconnect.clicked.connect(lambda: asyncio.create_task(self.ws.disconnect()))
        self.btn_clear.clicked.connect(self.log_view.clear)
        for btn in (self.btn_connect, self.btn_disconnect, self.btn_clear):
            btn.setMinimumHeight(34)
            top.addWidget(btn)

        layout.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(8)

        market_card, mg = self._make_card("MARKET")
        market_card.setMinimumWidth(320)
        self.lbl_symbol = self._make_value_label(14)
        self.lbl_symbol.setText(SYMBOL)
        self.lbl_last = self._make_value_label(30)
        self.lbl_bid = self._make_value_label(16)
        self.lbl_ask = self._make_value_label(16)
        self.lbl_spread = self._make_value_label(16)
        self.lbl_age = self._make_value_label(12)
        self.lbl_tick_rate = self._make_value_label(12)
        self.led_tick_age, _ = self._create_led("")

        mg.addWidget(QLabel("Symbol"), 0, 0)
        mg.addWidget(self.lbl_symbol, 0, 1)
        mg.addWidget(QLabel("Last Price"), 1, 0)
        mg.addWidget(self.lbl_last, 1, 1)
        mg.addWidget(QLabel("Bid"), 2, 0)
        mg.addWidget(self.lbl_bid, 2, 1)
        mg.addWidget(QLabel("Ask"), 3, 0)
        mg.addWidget(self.lbl_ask, 3, 1)
        mg.addWidget(QLabel("Spread %"), 4, 0)
        mg.addWidget(self.lbl_spread, 4, 1)
        mg.addWidget(QLabel("Tick age"), 5, 0)
        age_wrap = QHBoxLayout()
        age_wrap.setContentsMargins(0, 0, 0, 0)
        age_wrap.addWidget(self.led_tick_age)
        age_wrap.addWidget(self.lbl_age, 1)
        mg.addLayout(age_wrap, 5, 1)
        mg.addWidget(QLabel("Tick rate"), 6, 0)
        mg.addWidget(self.lbl_tick_rate, 6, 1)

        radar_card, dg = self._make_card("DETECTOR RADAR")
        radar_card.setMinimumWidth(540)
        self.lbl_det_phase = self._make_value_label(22, Qt.AlignmentFlag.AlignLeft)
        self.lbl_det_score = self._make_value_label(30, Qt.AlignmentFlag.AlignLeft)
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setValue(0)
        self.score_bar.setTextVisible(True)
        self.score_bar.setFormat("%p%")
        self.lbl_signal = self._make_value_label(16)
        self.lbl_reason = self._make_value_label(14, Qt.AlignmentFlag.AlignLeft)
        self.lbl_reason_codes = self._make_value_label(11, Qt.AlignmentFlag.AlignLeft)
        self.lbl_reason_codes.setWordWrap(True)
        self.lbl_reason_codes.setMaximumHeight(44)
        self.lbl_setup_age = self._make_value_label(12)
        self.lbl_reclaim_hold = self._make_value_label(12)
        self.lbl_last_invalid = self._make_value_label(12, Qt.AlignmentFlag.AlignLeft)

        dg.addWidget(QLabel("PHASE"), 0, 0)
        dg.addWidget(self.lbl_det_phase, 0, 1)
        dg.addWidget(QLabel("SCORE"), 1, 0)
        dg.addWidget(self.lbl_det_score, 1, 1)
        dg.addWidget(self.score_bar, 2, 0, 1, 2)
        dg.addWidget(QLabel("Signal lamp"), 3, 0)
        dg.addWidget(self.lbl_signal, 3, 1)
        dg.addWidget(QLabel("Reason"), 4, 0)
        dg.addWidget(self.lbl_reason, 4, 1)
        dg.addWidget(self.lbl_reason_codes, 5, 0, 1, 2)
        dg.addWidget(QLabel("Setup age"), 6, 0)
        dg.addWidget(self.lbl_setup_age, 6, 1)
        dg.addWidget(QLabel("Reclaim hold"), 7, 0)
        dg.addWidget(self.lbl_reclaim_hold, 7, 1)
        dg.addWidget(QLabel("Last invalid"), 8, 0)
        dg.addWidget(self.lbl_last_invalid, 8, 1)

        analyzer_card, ag = self._make_card("ANALYZER")
        analyzer_card.setMinimumWidth(340)
        self.lbl_fast_drop = self._make_value_label(16)
        self.lbl_fast_bounce = self._make_value_label(16)
        self.lbl_speed = self._make_value_label(16)
        self.lbl_volatility = self._make_value_label(16)
        self.lbl_spread_avg = self._make_value_label(16)
        self.lbl_state = self._make_value_label(14)

        self.bar_drop = QProgressBar(); self.bar_drop.setRange(0, 100)
        self.bar_bounce = QProgressBar(); self.bar_bounce.setRange(0, 100)
        self.bar_speed = QProgressBar(); self.bar_speed.setRange(0, 100)
        self.bar_volatility = QProgressBar(); self.bar_volatility.setRange(0, 100)
        self.bar_spread = QProgressBar(); self.bar_spread.setRange(0, 100)
        for bar in (self.bar_drop, self.bar_bounce, self.bar_speed, self.bar_volatility, self.bar_spread):
            bar.setTextVisible(False)
            bar.setFixedHeight(8)

        items = [
            ("Drop %", self.lbl_fast_drop, self.bar_drop),
            ("Bounce %", self.lbl_fast_bounce, self.bar_bounce),
            ("Speed", self.lbl_speed, self.bar_speed),
            ("Volatility", self.lbl_volatility, self.bar_volatility),
            ("Spread avg", self.lbl_spread_avg, self.bar_spread),
        ]
        row = 0
        for title, value, bar in items:
            ag.addWidget(QLabel(title), row, 0)
            ag.addWidget(value, row, 1)
            row += 1
            ag.addWidget(bar, row, 0, 1, 2)
            row += 1

        ag.addWidget(QLabel("FSM state"), row, 0)
        ag.addWidget(self.lbl_state, row, 1)

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
            QLabel#value[size="22"] { font-size: 22px; font-weight: 700; color: #9ed0ff; }
            QLabel#value[size="16"] { font-size: 16px; font-weight: 600; }
            QLabel#value[size="14"] { font-size: 14px; font-weight: 600; }
            QLabel#value[size="12"] { font-size: 12px; }
            QLabel#value[size="11"] { font-size: 11px; color:#8da2c4; }
            #ledLabel { font-size: 11px; color: #c3d7f7; font-weight: 600; }
            #ledLamp { border-radius: 8px; border: 1px solid #24395d; }
            #ledLamp[status="off"] { background: #64748b; }
            #ledLamp[status="green"] { background: #32d296; }
            #ledLamp[status="blue"] { background: #60a5fa; }
            #ledLamp[status="orange"] { background: #fb923c; }
            #ledLamp[status="red"] { background: #ef4444; }
            QPushButton { background: #1e2c49; color: #e2eeff; border: 1px solid #2d4570; border-radius: 8px; padding: 8px 12px; font-size: 12px; font-weight: 700; }
            QPushButton:hover { background: #2c4067; }
            QPushButton:pressed { background: #15213a; }
            QProgressBar { background:#0f1729; border:1px solid #2a3d5e; border-radius:5px; height:18px; color:#dff3ff; }
            QProgressBar::chunk { background:#32d296; border-radius:4px; }
            #logView { background: #0f1729; border: 1px solid #1f2e4b; border-radius: 8px; font-size: 11px; font-family: "Consolas", "Courier New", monospace; }
            """
        )

    def _update_leds(self, quality: str, phase: str, signal: str, tick_age_ms: int) -> None:
        self._set_led(self.led_data, {"GOOD": "green", "WAITING": "off", "STALE": "orange", "BAD_SPREAD": "red"}.get(quality, "off"))
        self._set_led(self.led_drop, "blue" if phase == "WATCHING_DROP" else ("orange" if phase == "LIQUIDITY_SWEEP" else "off"))
        self._set_led(self.led_sweep, "orange" if phase == "LIQUIDITY_SWEEP" else "off")
        self._set_led(self.led_reclaim, "orange" if phase == "RECLAIM_WAIT" else ("green" if "RECLAIM_CONFIRMED" in signal else "off"))
        self._set_led(self.led_signal, "green" if signal == "LONG_SIGNAL" else "off")
        block = "off"
        if phase == "INVALIDATED":
            block = "red"
        elif quality in {"HIGH_SPREAD", "STALE", "BAD_SPREAD"}:
            block = "orange" if quality == "HIGH_SPREAD" else "red"
        self._set_led(self.led_block, block)

        tick_status = "green" if tick_age_ms < 1000 else "orange" if tick_age_ms <= 3000 else "red"
        self._set_led(self.led_tick_age, tick_status)

    def append_log(self, message: str) -> None:
        self.log_view.append(message)

    def on_status(self, status: str) -> None:
        status_map = {"CONNECTED": "green", "DISCONNECTED": "off", "STALE": "orange"}
        self._set_led(self.led_ws, status_map.get(status, "off"))

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

        self.lbl_det_phase.setText(signal.phase)
        self.lbl_det_score.setText(f"{signal.score:.2f}")
        self.score_bar.setValue(max(0, min(100, int(signal.score))))
        self.lbl_reason_codes.setText(" | ".join(signal.reason_codes) if signal.reason_codes else "-")
        self.lbl_reason.setText(signal.human_reason)
        self.lbl_setup_age.setText(f"{signal.setup_age_ms} ms")
        self.lbl_reclaim_hold.setText(f"{signal.reclaim_hold_ms} ms")
        self.lbl_last_invalid.setText(signal.last_invalid_reason)

        self.lbl_state.setText(result.state)
        self.lbl_signal.setText("LONG READY" if result.signal == "LONG_SIGNAL" else "OFF")

        self.bar_drop.setValue(min(100, int(abs(fast_metrics.drop_pct) * 3000)))
        self.bar_bounce.setValue(min(100, int(abs(fast_metrics.bounce_pct) * 3000)))
        self.bar_speed.setValue(min(100, int(abs(fast_metrics.impulse_speed_pct_per_sec) * 500)))
        self.bar_volatility.setValue(min(100, int(abs(fast_metrics.volatility_pct) * 4000)))
        self.bar_spread.setValue(min(100, int(abs(fast_metrics.spread_avg_pct) * 8000)))

        self._update_leds(quality, signal.phase, result.signal, int(time.time() * 1000) - tick.ts_ms)

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
            self._set_led(self.led_tick_age, "off")
            return
        age = now - last.ts_ms
        stale = self.buffer.is_stale(STALE_MS, now)
        age_text = f"{age} ms"
        if stale:
            age_text += " (STALE)"
            self.on_status("STALE")
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
