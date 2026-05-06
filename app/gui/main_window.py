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
from app.logger import setup_logging
from app.market_buffer import MarketBuffer
from app.market_ws import MarketWSClient
from app.strategy.liquidity_grab_fsm import LiquidityGrabFSM


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(980, 720)

        self.buffer = MarketBuffer(maxlen=MAX_BUFFER)
        self.fsm = LiquidityGrabFSM(max_allowed_spread_pct=MAX_ALLOWED_SPREAD_PCT)
        self.analyzer = DataAnalyzer(
            AnalyzerConfig(
                fast_window_ms=FAST_WINDOW_MS,
                mid_window_ms=MID_WINDOW_MS,
                slow_window_ms=SLOW_WINDOW_MS,
                min_ticks_fast=MIN_TICKS_FAST,
                stale_after_ms=STALE_AFTER_MS,
            )
        )

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.logger = setup_logging(self.append_log)
        self._last_analysis_log_ms = 0

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
        self.lbl_symbol = QLabel(SYMBOL)
        self.lbl_last = QLabel("-")
        self.lbl_bid = QLabel("-")
        self.lbl_ask = QLabel("-")
        self.lbl_spread = QLabel("-")
        self.lbl_ws = QLabel("DISCONNECTED")
        self.lbl_age = QLabel("-")
        rows = [
            ("Symbol", self.lbl_symbol),
            ("Last Price", self.lbl_last),
            ("Bid", self.lbl_bid),
            ("Ask", self.lbl_ask),
            ("Spread %", self.lbl_spread),
            ("WS status", self.lbl_ws),
            ("Last tick age", self.lbl_age),
        ]
        for i, (k, v) in enumerate(rows):
            mg.addWidget(QLabel(k), i, 0)
            mg.addWidget(v, i, 1)

        analyzer_box = QGroupBox("Data Analyzer")
        ag = QGridLayout(analyzer_box)
        self.lbl_fast_drop = QLabel("-")
        self.lbl_fast_bounce = QLabel("-")
        self.lbl_speed = QLabel("-")
        self.lbl_volatility = QLabel("-")
        self.lbl_spread_avg = QLabel("-")
        self.lbl_tick_rate = QLabel("-")
        self.lbl_data_quality = QLabel("WAITING")
        arows = [
            ("Fast drop %", self.lbl_fast_drop),
            ("Fast bounce %", self.lbl_fast_bounce),
            ("Speed %/sec", self.lbl_speed),
            ("Volatility %", self.lbl_volatility),
            ("Spread avg %", self.lbl_spread_avg),
            ("Tick rate", self.lbl_tick_rate),
            ("Data quality", self.lbl_data_quality),
        ]
        for i, (k, v) in enumerate(arows):
            ag.addWidget(QLabel(k), i, 0)
            ag.addWidget(v, i, 1)

        strat_box = QGroupBox("Strategy Status")
        sg = QGridLayout(strat_box)
        self.lbl_state = QLabel("INIT")
        self.lbl_signal = QLabel("NO_SIGNAL")
        self.lbl_reason = QLabel("core kernel only")
        srows = [
            ("FSM State", self.lbl_state),
            ("Signal", self.lbl_signal),
            ("Reason", self.lbl_reason),
        ]
        for i, (k, v) in enumerate(srows):
            sg.addWidget(QLabel(k), i, 0)
            sg.addWidget(v, i, 1)

        layout.addLayout(btn_row)
        layout.addWidget(market_box)
        layout.addWidget(analyzer_box)
        layout.addWidget(strat_box)
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

        metrics_map = self.analyzer.analyze(self.buffer)
        fast_metrics = metrics_map["fast"]
        result = self.fsm.evaluate(fast_metrics)

        self.lbl_fast_drop.setText(f"{fast_metrics.drop_pct:.5f}")
        self.lbl_fast_bounce.setText(f"{fast_metrics.bounce_pct:.5f}")
        self.lbl_speed.setText(f"{fast_metrics.impulse_speed_pct_per_sec:.5f}")
        self.lbl_volatility.setText(f"{fast_metrics.volatility_pct:.5f}")
        self.lbl_spread_avg.setText(f"{fast_metrics.spread_avg_pct:.5f}")
        self.lbl_tick_rate.setText(f"{fast_metrics.tick_rate:.2f} t/s")
        quality = self._quality_label(fast_metrics)
        self.lbl_data_quality.setText(quality)

        self.lbl_state.setText(result.state)
        self.lbl_signal.setText(result.signal)
        self.lbl_reason.setText(result.reason)

        if tick.ts_ms - self._last_analysis_log_ms >= ANALYSIS_LOG_INTERVAL_MS:
            self._last_analysis_log_ms = tick.ts_ms
            self.logger.info(
                "Analyzer drop=%.5f bounce=%.5f speed=%.5f spread=%.5f tick_rate=%.2f quality=%s",
                fast_metrics.drop_pct,
                fast_metrics.bounce_pct,
                fast_metrics.impulse_speed_pct_per_sec,
                fast_metrics.spread_avg_pct,
                fast_metrics.tick_rate,
                quality,
            )

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
