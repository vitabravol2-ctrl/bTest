import asyncio
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
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
    APP_NAME,
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
        self.setWindowTitle(APP_NAME)
        self.resize(980, 760)

        self.buffer = MarketBuffer(maxlen=MAX_BUFFER)
        self.fsm = LiquidityGrabFSM()
        self.detector = LiquidityGrabDetector()
        self.analyzer = DataAnalyzer(
            AnalyzerConfig(FAST_WINDOW_MS, MID_WINDOW_MS, SLOW_WINDOW_MS, MIN_TICKS_FAST, STALE_AFTER_MS)
        )

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.logger = setup_logging(self.append_log)
        self._last_analysis_log_ms = 0
        self._last_detector_log_ms = 0

        self.ws = MarketWSClient(self.logger)
        self.ws.tick_received.connect(self.on_tick)
        self.ws.status_changed.connect(self.on_status)
        self.ws.error.connect(self.on_error)

        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_age)
        self.timer.start(500)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        btn_row = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_clear = QPushButton("Clear Log")
        self.btn_connect.clicked.connect(lambda: asyncio.create_task(self.ws.connect()))
        self.btn_disconnect.clicked.connect(lambda: asyncio.create_task(self.ws.disconnect()))
        self.btn_clear.clicked.connect(self.log_view.clear)
        btn_row.addWidget(self.btn_connect)
        btn_row.addWidget(self.btn_disconnect)
        btn_row.addWidget(self.btn_clear)
        btn_row.addStretch()

        market_box = QGroupBox("Market Status")
        mg = QGridLayout(market_box)
        self.lbl_symbol, self.lbl_last, self.lbl_bid, self.lbl_ask = QLabel(SYMBOL), QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_spread, self.lbl_ws, self.lbl_age = QLabel("-"), QLabel("DISCONNECTED"), QLabel("-")
        for i, (k, v) in enumerate([
            ("Symbol", self.lbl_symbol), ("Last Price", self.lbl_last), ("Bid", self.lbl_bid), ("Ask", self.lbl_ask),
            ("Spread %", self.lbl_spread), ("WS status", self.lbl_ws), ("Last tick age", self.lbl_age),
        ]):
            mg.addWidget(QLabel(k), i, 0)
            mg.addWidget(v, i, 1)

        analyzer_box = QGroupBox("Data Analyzer")
        ag = QGridLayout(analyzer_box)
        self.lbl_fast_drop, self.lbl_fast_bounce, self.lbl_speed = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_volatility, self.lbl_spread_avg, self.lbl_tick_rate = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_data_quality = QLabel("WAITING")
        for i, (k, v) in enumerate([
            ("Fast drop %", self.lbl_fast_drop), ("Fast bounce %", self.lbl_fast_bounce), ("Speed %/sec", self.lbl_speed),
            ("Volatility %", self.lbl_volatility), ("Spread avg %", self.lbl_spread_avg), ("Tick rate", self.lbl_tick_rate),
            ("Data quality", self.lbl_data_quality),
        ]):
            ag.addWidget(QLabel(k), i, 0)
            ag.addWidget(v, i, 1)

        det_box = QGroupBox("Liquidity Grab Detector")
        dg = QGridLayout(det_box)
        self.lbl_det_phase, self.lbl_det_score, self.lbl_det_side = QLabel("NO_SETUP"), QLabel("0.0"), QLabel("NONE")
        self.lbl_trigger, self.lbl_grab_low, self.lbl_reclaim = QLabel("-"), QLabel("-"), QLabel("-")
        self.lbl_reason_codes, self.lbl_human_reason = QLabel("-"), QLabel("-")
        self.lbl_reason_codes.setWordWrap(True)
        self.lbl_human_reason.setWordWrap(True)
        for i, (k, v) in enumerate([
            ("Phase", self.lbl_det_phase), ("Score", self.lbl_det_score), ("Side", self.lbl_det_side),
            ("Trigger price", self.lbl_trigger), ("Grab low", self.lbl_grab_low), ("Reclaim level", self.lbl_reclaim),
            ("Reason codes", self.lbl_reason_codes), ("Human reason", self.lbl_human_reason),
        ]):
            dg.addWidget(QLabel(k), i, 0)
            dg.addWidget(v, i, 1)

        strat_box = QGroupBox("Strategy Status")
        sg = QGridLayout(strat_box)
        self.lbl_state, self.lbl_signal, self.lbl_reason = QLabel("IDLE"), QLabel("NO_SIGNAL"), QLabel("detector idle")
        for i, (k, v) in enumerate([("FSM State", self.lbl_state), ("Signal", self.lbl_signal), ("Reason", self.lbl_reason)]):
            sg.addWidget(QLabel(k), i, 0)
            sg.addWidget(v, i, 1)

        layout.addLayout(btn_row)
        for box in (market_box, analyzer_box, det_box, strat_box):
            layout.addWidget(box)
        layout.addWidget(self.log_view)

    def append_log(self, message: str) -> None:
        self.log_view.append(message)

    def on_status(self, status: str) -> None:
        self.lbl_ws.setText(status)

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
        self.lbl_data_quality.setText(self._quality_label(fast_metrics))

        self.lbl_det_phase.setText(signal.phase)
        self.lbl_det_score.setText(f"{signal.score:.2f}")
        self.lbl_det_side.setText(signal.side)
        self.lbl_trigger.setText("-" if signal.trigger_price is None else f"{signal.trigger_price:.2f}")
        self.lbl_grab_low.setText("-" if signal.grab_low is None else f"{signal.grab_low:.2f}")
        self.lbl_reclaim.setText("-" if signal.reclaim_level is None else f"{signal.reclaim_level:.2f}")
        self.lbl_reason_codes.setText(", ".join(signal.reason_codes) if signal.reason_codes else "-")
        self.lbl_human_reason.setText(signal.human_reason)

        self.lbl_state.setText(result.state)
        self.lbl_signal.setText(result.signal)
        self.lbl_reason.setText(result.reason)

        if tick.ts_ms - self._last_analysis_log_ms >= ANALYSIS_LOG_INTERVAL_MS:
            self._last_analysis_log_ms = tick.ts_ms
            self.logger.info("Analyzer drop=%.5f bounce=%.5f speed=%.5f spread=%.5f", fast_metrics.drop_pct, fast_metrics.bounce_pct, fast_metrics.impulse_speed_pct_per_sec, fast_metrics.spread_avg_pct)

        if tick.ts_ms - self._last_detector_log_ms >= DETECTOR_LOG_INTERVAL_MS:
            self._last_detector_log_ms = tick.ts_ms
            self.logger.info("Detector phase=%s score=%.2f side=%s reasons=%s detected=%s", signal.phase, signal.score, signal.side, signal.reason_codes, signal.detected)
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
        self.lbl_age.setText(f"{age} ms{' (STALE)' if stale else ''}")

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
