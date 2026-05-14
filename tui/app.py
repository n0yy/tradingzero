from queue import Queue, Empty

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Footer, RichLog, Static
from textual.containers import Horizontal
from textual import work


class MetricBox(Static):
    DEFAULT_CSS = """
    MetricBox {
        border: solid #2a2a2a;
        padding: 0 1;
        height: 5;
        width: 1fr;
        content-align: center middle;
        text-align: center;
    }
    """

    def set_value(self, label: str, value: str, value_style: str = "bold white") -> None:
        text = Text(justify="center")
        text.append(f"{label}\n", style="dim white")
        text.append(value, style=value_style)
        self.update(text)


class MetricsBar(Horizontal):
    DEFAULT_CSS = """
    MetricsBar {
        height: 5;
    }
    """

    def compose(self) -> ComposeResult:
        yield MetricBox(id="tile-generation")
        yield MetricBox(id="tile-progress")
        yield MetricBox(id="tile-sharpe")
        yield MetricBox(id="tile-best-sharpe")
        yield MetricBox(id="tile-balance")
        yield MetricBox(id="tile-pnl")
        yield MetricBox(id="tile-promotions")
        yield MetricBox(id="tile-status")


class ChartPanel(Static):
    """Sparkline-style Sharpe chart rendered with pure Rich markup."""

    DEFAULT_CSS = """
    ChartPanel {
        border: solid #1a3a6b;
        height: 1fr;
        padding: 0 1;
        overflow: hidden hidden;
    }
    """

    BARS = " ▁▂▃▄▅▆▇█"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sharpe_history: list[float] = []

    def add_point(self, sharpe: float) -> None:
        self._sharpe_history.append(sharpe)
        self._render_chart()

    def on_resize(self) -> None:
        self._render_chart()

    def _render_chart(self) -> None:
        if not self._sharpe_history:
            self.update("[dim]Waiting for data…[/dim]")
            return

        inner_w = max(self.size.width - 4, 10)
        inner_h = max(self.size.height - 4, 4)

        data = self._sharpe_history
        visible = data[-inner_w:]
        n = len(visible)

        if n < 2:
            self.update("[dim]Waiting for data…[/dim]")
            return

        lo = min(visible)
        hi = max(visible)
        # if all values identical, show flat line in middle
        if hi == lo:
            mid_label = f"{hi:+.2f} "
            flat_color = "green" if hi >= 0 else "red"
            flat_char = "─"
            lines = []
            for row in range(inner_h):
                if row == inner_h // 2:
                    lines.append(f"[dim]{mid_label}[/dim]" + f"[{flat_color}]{flat_char * n}[/{flat_color}]")
                else:
                    lines.append(f"[dim]{'':7}[/dim]")
            x_axis = " " * 7 + "─" * n
            pad = max(n - 5 - len(str(len(data))), 1)
            gen_label = " " * 7 + "1" + " " * pad + str(len(data))
            last = data[-1]
            trend_color = "green" if last >= 0 else "red"
            header = f"[bold]Sharpe Ratio[/bold]  [{trend_color}]── {last:+.4f}[/{trend_color}]  [dim]({n} of {len(data)} gens shown)[/dim]"
            self.update(header + "\n" + "\n".join(lines) + "\n" + x_axis + "\n" + gen_label)
            return

        span = hi - lo

        lines: list[str] = []
        for row in range(inner_h):
            threshold = hi - (row / max(inner_h - 1, 1)) * span
            y_label = f"{threshold:+.2f} "
            row_chars: list[str] = []
            for val in visible:
                normalized = (val - lo) / span
                row_fill = normalized * inner_h
                row_idx = inner_h - 1 - row
                cell_fill = max(0.0, min(1.0, row_fill - row_idx))
                bar_idx = int(cell_fill * (len(self.BARS) - 1))
                char = self.BARS[bar_idx]
                color = "green" if val >= 0 else "red"
                row_chars.append(f"[{color}]{char}[/{color}]")
            lines.append(f"[dim]{y_label}[/dim]" + "".join(row_chars))

        x_axis = " " * 7 + "─" * n
        pad = max(n - 5 - len(str(len(data))), 1)
        gen_label = " " * 7 + "1" + " " * pad + str(len(data))

        last = data[-1]
        trend = "▲" if data[-1] > data[-2] else "▼"
        trend_color = "green" if last >= 0 else "red"
        header = f"[bold]Sharpe Ratio[/bold]  [{trend_color}]{trend} {last:+.4f}[/{trend_color}]  [dim]({n} of {len(data)} gens shown)[/dim]"

        self.update(header + "\n" + "\n".join(lines) + "\n" + x_axis + "\n" + gen_label)


class TUIApp(App):
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen {
        layout: vertical;
        background: #0d0d0d;
    }

    MetricBox#tile-sharpe {
        border: solid #1a6b1a;
    }

    MetricBox#tile-best-sharpe {
        border: solid #1a6b1a;
    }

    MetricBox#tile-balance {
        border: solid #1a4a6b;
    }

    MetricBox#tile-pnl {
        border: solid #2a2a2a;
    }

    MetricBox#tile-status {
        border: solid #6b1a1a;
    }

    ChartPanel {
        border: solid #1a3a6b;
    }

    RichLog {
        border: solid #2a2a2a;
        height: 12;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, update_queue: Queue, **kwargs):
        super().__init__(**kwargs)
        self.update_queue = update_queue
        self._promotions = 0
        self._total_generations = 0
        self._initial_balance = 0.0
        self._stop_requested = False

    def compose(self) -> ComposeResult:
        yield MetricsBar()
        yield ChartPanel(id="chart")
        yield RichLog(id="log", highlight=True, markup=True, max_lines=200)
        yield Footer()

    def on_mount(self) -> None:
        self._init_tiles()
        self._poll_queue()

    def _init_tiles(self) -> None:
        self.query_one("#tile-generation", MetricBox).set_value("Generation", "—")
        self.query_one("#tile-progress", MetricBox).set_value("Progress", "—")
        self.query_one("#tile-sharpe", MetricBox).set_value("Sharpe", "—", "bold green")
        self.query_one("#tile-best-sharpe", MetricBox).set_value("Best Sharpe", "—", "bold green")
        self.query_one("#tile-balance", MetricBox).set_value("Balance", "—", "bold cyan")
        self.query_one("#tile-pnl", MetricBox).set_value("PnL", "—", "bold white")
        self.query_one("#tile-promotions", MetricBox).set_value("Promotions", "0", "bold magenta")
        self.query_one("#tile-status", MetricBox).set_value("Status", "TRAINING", "bold yellow")

    @work(thread=True)
    def _poll_queue(self) -> None:
        while not self._stop_requested:
            try:
                payload = self.update_queue.get(timeout=0.1)
                self.call_from_thread(self._handle_update, payload)
            except Empty:
                continue

    def _handle_update(self, payload: dict) -> None:
        if payload.get("type") == "stop":
            self._stop_requested = True
            self.query_one("#tile-status", MetricBox).set_value("Status", "DONE", "bold green")
            return

        if payload.get("promoted"):
            self._promotions += 1

        generation = payload.get("generation", 0)
        current_sharpe = payload.get("current_sharpe", 0.0)
        best_sharpe = payload.get("best_sharpe", 0.0)
        promoted = payload.get("promoted", False)
        total = payload.get("total_generations", self._total_generations) or generation
        final_balance = payload.get("final_balance", None)
        pnl = payload.get("pnl", None)
        initial_balance = payload.get("initial_balance", self._initial_balance)

        if total:
            self._total_generations = total
        if initial_balance:
            self._initial_balance = initial_balance

        progress_pct = f"{generation / total * 100:.1f}%" if total else "—"
        sharpe_style = "bold green" if current_sharpe >= 0 else "bold red"

        self.query_one("#tile-generation", MetricBox).set_value(
            "Generation", f"{generation} / {total or '?'}"
        )
        self.query_one("#tile-progress", MetricBox).set_value(
            "Progress", progress_pct, "bold cyan"
        )
        self.query_one("#tile-sharpe", MetricBox).set_value(
            "Sharpe", f"{current_sharpe:.4f}", sharpe_style
        )
        self.query_one("#tile-best-sharpe", MetricBox).set_value(
            "Best Sharpe", f"{best_sharpe:.4f}", "bold green"
        )

        if final_balance is not None:
            self.query_one("#tile-balance", MetricBox).set_value(
                "Balance", f"${final_balance:,.2f}", "bold cyan"
            )
        if pnl is not None:
            pnl_style = "bold green" if pnl >= 0 else "bold red"
            pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"-${abs(pnl):,.2f}"
            self.query_one("#tile-pnl", MetricBox).set_value("PnL", pnl_str, pnl_style)

        self.query_one("#tile-promotions", MetricBox).set_value(
            "Promotions", str(self._promotions), "bold magenta"
        )
        if promoted:
            self.query_one("#tile-status", MetricBox).set_value(
                "Status", "★ PROMOTED", "bold green"
            )
        else:
            self.query_one("#tile-status", MetricBox).set_value(
                "Status", "TRAINING", "bold yellow"
            )

        self.query_one("#chart", ChartPanel).add_point(current_sharpe)

        sharpe_color = "green" if current_sharpe >= 0 else "red"
        pnl_log = ""
        if pnl is not None:
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_sign = "+" if pnl >= 0 else "-"
            pnl_log = f" | pnl=[{pnl_color}]{pnl_sign}${abs(pnl):,.2f}[/{pnl_color}]"
        msg = (
            f"[cyan]Gen {generation}[/cyan]"
            f" | sharpe=[{sharpe_color}]{current_sharpe:.4f}[/{sharpe_color}]"
            f" | best=[green]{best_sharpe:.4f}[/green]"
            f"{pnl_log}"
        )
        if promoted:
            msg += " | [bold green]★ PROMOTED[/bold green]"
        self.query_one("#log", RichLog).write(msg)

    def action_quit(self) -> None:
        self._stop_requested = True
        self.exit()
