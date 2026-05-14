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
        yield MetricBox(id="tile-winrate")
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
        super().__init__("[dim]Waiting for data…[/dim]", **kwargs)
        self._sharpe_history: list[float] = []

    def on_mount(self) -> None:
        self._render_chart()

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


class ActionPanel(Static):
    DEFAULT_CSS = """
    ActionPanel {
        border: solid #3a1a6b;
        height: 1fr;
        padding: 0 1;
        overflow: hidden hidden;
    }
    """

    FULL_BLOCK = "█"
    BAR_WIDTH = 6

    def __init__(self, **kwargs):
        super().__init__("[dim]—[/dim]", **kwargs)
        self._action_counts: dict | None = None
        self._last_action: int | None = None
        self._cumulative_buys: int = 0
        self._cumulative_sells: int = 0

    def on_mount(self) -> None:
        self._draw()

    def set_data(
        self,
        action_counts: dict,
        last_action: int,
        cumulative_buys: int,
        cumulative_sells: int,
    ) -> None:
        self._action_counts = action_counts
        self._last_action = last_action
        self._cumulative_buys = cumulative_buys
        self._cumulative_sells = cumulative_sells
        self._draw()

    def _draw(self) -> None:
        if self._action_counts is None:
            self.update("[dim]—[/dim]")
            return

        counts = self._action_counts
        total = counts.get("buy", 0) + counts.get("hold", 0) + counts.get("sell", 0)

        def bar(n: int) -> str:
            filled = round((n / total) * self.BAR_WIDTH) if total > 0 else 0
            return self.FULL_BLOCK * filled + " " * (self.BAR_WIDTH - filled)

        buy_pct = counts.get("buy", 0) / total * 100 if total > 0 else 0
        hold_pct = counts.get("hold", 0) / total * 100 if total > 0 else 0
        sell_pct = counts.get("sell", 0) / total * 100 if total > 0 else 0

        action_labels = {0: "HOLD", 1: "BUY", 2: "SELL"}
        action_colors = {0: "dim", 1: "green", 2: "red"}
        last = self._last_action if self._last_action is not None else 0
        last_label = action_labels.get(last, "HOLD")
        last_color = action_colors.get(last, "dim")

        lines = [
            "[bold dim]Action Distribution[/bold dim]",
            f"[green]BUY  {bar(counts.get('buy', 0))} {buy_pct:4.0f}%[/green]",
            f"[dim]HOLD {bar(counts.get('hold', 0))} {hold_pct:4.0f}%[/dim]",
            f"[red]SELL {bar(counts.get('sell', 0))} {sell_pct:4.0f}%[/red]",
            "",
            "[bold dim]Last Action[/bold dim]",
            f"[{last_color}]{last_label}[/{last_color}]",
            "",
            "[bold dim]Cumul Trades[/bold dim]",
            f"[green]BUY  {self._cumulative_buys}[/green]",
            f"[red]SELL {self._cumulative_sells}[/red]",
        ]
        self.update("\n".join(lines))


class PricePanel(Static):
    DEFAULT_CSS = """
    PricePanel {
        border: solid #1a6b3a;
        height: 1fr;
        padding: 0 1;
        overflow: hidden hidden;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("[dim]—[/dim]", **kwargs)
        self._prices: list[float] = []
        self._actions: list[int] = []

    def on_mount(self) -> None:
        self._draw()

    def set_data(self, prices: list[float], actions: list[int]) -> None:
        self._prices = prices
        self._actions = actions
        self._draw()

    def on_resize(self) -> None:
        self._draw()

    def _draw(self) -> None:
        if len(self._prices) < 2:
            self.update("[dim]—[/dim]")
            return

        try:
            import plotext as plt
            plt.clf()
            plt.plotsize(max(self.size.width - 4, 20), max(self.size.height - 2, 6))
            plt.plot(self._prices, color="cyan")

            buy_x = [i for i, a in enumerate(self._actions) if a == 1]
            buy_y = [self._prices[i] for i in buy_x]
            sell_x = [i for i, a in enumerate(self._actions) if a == 2]
            sell_y = [self._prices[i] for i in sell_x]

            if buy_x:
                plt.scatter(buy_x, buy_y, color="green", marker="▲")
            if sell_x:
                plt.scatter(sell_x, sell_y, color="red", marker="▼")

            self.update(plt.build())
        except Exception:
            self.update("[dim]—[/dim]")


class ChartArea(Horizontal):
    DEFAULT_CSS = """
    ChartArea {
        height: 1fr;
    }
    ChartArea ChartPanel {
        width: 2fr;
    }
    ChartArea PricePanel {
        width: 2fr;
    }
    ChartArea ActionPanel {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield ChartPanel(id="chart")
        yield PricePanel(id="price-panel")
        yield ActionPanel(id="action-panel")


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
        height: 4;
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
        yield ChartArea()
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
        self.query_one("#tile-winrate", MetricBox).set_value("Win Rate", "—", "bold white")
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

    def _update_winrate_tile(self, tile: "MetricBox", win_rate: float) -> None:
        style = "bold green" if win_rate >= 0.5 else "bold red"
        tile.set_value("Win Rate", f"{win_rate * 100:.0f}%", style)

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

        win_rate = payload.get("win_rate", None)
        if win_rate is not None:
            self._update_winrate_tile(self.query_one("#tile-winrate", MetricBox), win_rate)

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

        action_counts = payload.get("action_counts", None)
        if action_counts is not None:
            self.query_one("#action-panel", ActionPanel).set_data(
                action_counts=action_counts,
                last_action=payload.get("action_series", [0])[-1] if payload.get("action_series") else 0,
                cumulative_buys=payload.get("cumulative_buys", 0),
                cumulative_sells=payload.get("cumulative_sells", 0),
            )

        price_series = payload.get("price_series", None)
        action_series = payload.get("action_series", None)
        if price_series is not None and action_series is not None:
            self.query_one("#price-panel", PricePanel).set_data(
                prices=price_series,
                actions=action_series,
            )

        sharpe_color = "green" if current_sharpe >= 0 else "red"
        pnl_log = ""
        if pnl is not None:
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_sign = "+" if pnl >= 0 else "-"
            pnl_log = f" | pnl=[{pnl_color}]{pnl_sign}${abs(pnl):,.2f}[/{pnl_color}]"
        win_log = ""
        if win_rate is not None:
            win_log = f" | win={win_rate * 100:.0f}%"
        msg = (
            f"[cyan]Gen {generation}[/cyan]"
            f" | sharpe=[{sharpe_color}]{current_sharpe:.4f}[/{sharpe_color}]"
            f" | best=[green]{best_sharpe:.4f}[/green]"
            f"{pnl_log}"
            f"{win_log}"
        )
        if promoted:
            msg += " | [bold green]★ PROMOTED[/bold green]"
        self.query_one("#log", RichLog).write(msg)

    def action_quit(self) -> None:
        self._stop_requested = True
        self.exit()
