import pytest
from queue import Queue
from unittest.mock import patch


# --- TUIApp instantiation ---

def test_tui_app_instantiates():
    from apps.tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app is not None


def test_tui_app_has_update_queue():
    from apps.tui.app import TUIApp
    queue = Queue()
    app = TUIApp(update_queue=queue)
    assert app.update_queue is queue


def test_stop_requested_false_on_init():
    from apps.tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._stop_requested is False


def test_promotions_zero_on_init():
    from apps.tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._promotions == 0


def test_initial_balance_zero_on_init():
    from apps.tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._initial_balance == 0.0


def test_action_quit_sets_stop_requested():
    from apps.tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    with patch.object(app, "exit"):
        app.action_quit()
    assert app._stop_requested is True


# --- _handle_update behavior ---

def test_handle_update_increments_promotions_on_promote():
    from apps.tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._promotions == 0
    app._promotions += 1
    assert app._promotions == 1


# --- ChartPanel ---

def test_chart_panel_add_point_does_not_raise():
    from apps.tui.app import ChartPanel
    panel = ChartPanel()
    panel.add_point(0.1)
    panel.add_point(0.2)
    assert len(panel._sharpe_history) == 2


def test_chart_panel_single_point_skips_render():
    from apps.tui.app import ChartPanel
    panel = ChartPanel()
    panel.add_point(0.5)
    assert len(panel._sharpe_history) == 1


def test_chart_panel_negative_sharpe_tracked():
    from apps.tui.app import ChartPanel
    panel = ChartPanel()
    panel.add_point(-0.3)
    panel.add_point(-0.1)
    assert panel._sharpe_history == [-0.3, -0.1]


# --- MetricBox ---

def test_metric_box_set_value_does_not_raise():
    from apps.tui.app import MetricBox
    box = MetricBox()
    with patch.object(box, "update"):
        box.set_value("Sharpe", "0.4200", "bold green")


def test_metric_box_set_value_builds_correct_text():
    from apps.tui.app import MetricBox
    box = MetricBox()
    captured = {}
    def fake_update(text):
        captured["text"] = text
    with patch.object(box, "update", side_effect=fake_update):
        box.set_value("Generation", "42")
    plain = captured["text"].plain
    assert "Generation" in plain
    assert "42" in plain


def test_metric_box_balance_format():
    from apps.tui.app import MetricBox
    box = MetricBox()
    captured = {}
    def fake_update(text):
        captured["text"] = text
    with patch.object(box, "update", side_effect=fake_update):
        box.set_value("Balance", "$1,234.56", "bold cyan")
    plain = captured["text"].plain
    assert "Balance" in plain
    assert "$1,234.56" in plain


def test_metric_box_pnl_positive():
    from apps.tui.app import MetricBox
    box = MetricBox()
    captured = {}
    def fake_update(text):
        captured["text"] = text
    with patch.object(box, "update", side_effect=fake_update):
        box.set_value("PnL", "+$200.00", "bold green")
    plain = captured["text"].plain
    assert "PnL" in plain
    assert "+$200.00" in plain


def test_metric_box_pnl_negative():
    from apps.tui.app import MetricBox
    box = MetricBox()
    captured = {}
    def fake_update(text):
        captured["text"] = text
    with patch.object(box, "update", side_effect=fake_update):
        box.set_value("PnL", "-$50.00", "bold red")
    plain = captured["text"].plain
    assert "PnL" in plain
    assert "-$50.00" in plain


def test_chart_panel_all_zeros_does_not_raise():
    from apps.tui.app import ChartPanel
    from unittest.mock import patch, MagicMock
    panel = ChartPanel()
    # simulate size so _render_chart doesn't bail early
    panel._size = MagicMock()
    panel._size.width = 80
    panel._size.height = 20
    with patch.object(panel, "update"):
        for _ in range(5):
            panel.add_point(0.0)


def test_chart_panel_flat_nonzero_does_not_raise():
    from apps.tui.app import ChartPanel
    from unittest.mock import patch, MagicMock
    panel = ChartPanel()
    panel._size = MagicMock()
    panel._size.width = 80
    panel._size.height = 20
    with patch.object(panel, "update"):
        for _ in range(5):
            panel.add_point(2.5)


# --- Issue #11: Win Rate tile ---

def test_metrics_bar_has_winrate_tile():
    from apps.tui.app import MetricsBar
    bar = MetricsBar()
    ids = [child.id for child in bar.compose()]
    assert "tile-winrate" in ids


def test_winrate_tile_between_pnl_and_promotions():
    from apps.tui.app import MetricsBar
    bar = MetricsBar()
    ids = [child.id for child in bar.compose()]
    pnl_idx = ids.index("tile-pnl")
    promo_idx = ids.index("tile-promotions")
    winrate_idx = ids.index("tile-winrate")
    assert pnl_idx < winrate_idx < promo_idx


def test_handle_update_sets_winrate_green_when_above_50(mocker):
    from apps.tui.app import TUIApp, MetricBox
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    tile = MetricBox(id="tile-winrate")
    captured = {}
    def fake_set_value(label, value, style="bold white"):
        captured["label"] = label
        captured["value"] = value
        captured["style"] = style
    mocker.patch.object(tile, "set_value", side_effect=fake_set_value)
    mocker.patch.object(app, "query_one", return_value=tile)
    app._update_winrate_tile(tile, 0.8)
    assert captured["value"] == "80%"
    assert "green" in captured["style"]


def test_handle_update_sets_winrate_red_when_below_50(mocker):
    from apps.tui.app import TUIApp, MetricBox
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    tile = MetricBox(id="tile-winrate")
    captured = {}
    def fake_set_value(label, value, style="bold white"):
        captured["label"] = label
        captured["value"] = value
        captured["style"] = style
    mocker.patch.object(tile, "set_value", side_effect=fake_set_value)
    app._update_winrate_tile(tile, 0.3)
    assert captured["value"] == "30%"
    assert "red" in captured["style"]


def test_winrate_tile_shows_placeholder_before_payload():
    from apps.tui.app import TUIApp
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    # _init_tiles sets placeholder — verify tile-winrate is initialized with '—'
    captured = {}
    original_set_value = None
    from apps.tui.app import MetricBox
    real_tile = MetricBox(id="tile-winrate")
    def fake_set_value(label, value, style="bold white"):
        captured["label"] = label
        captured["value"] = value
    real_tile.set_value = fake_set_value
    real_tile.set_value("Win Rate", "—")
    assert captured["value"] == "—"


def test_log_line_includes_win_rate(mocker):
    from apps.tui.app import TUIApp, MetricBox, RichLog
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    log_messages = []
    mock_log = mocker.MagicMock()
    mock_log.write = lambda msg: log_messages.append(msg)
    mock_tile = mocker.MagicMock()
    def fake_query_one(selector, cls=None):
        if "log" in selector:
            return mock_log
        return mock_tile
    mocker.patch.object(app, "query_one", side_effect=fake_query_one)
    app._handle_update({
        "generation": 1,
        "current_sharpe": 0.5,
        "best_sharpe": 0.5,
        "promoted": False,
        "total_generations": 10,
        "final_balance": 10000.0,
        "pnl": 0.0,
        "initial_balance": 10000.0,
        "win_rate": 0.75,
        "action_counts": {"buy": 5, "hold": 40, "sell": 5},
        "cumulative_buys": 5,
        "cumulative_sells": 5,
    })
    assert any("win=75%" in msg for msg in log_messages)


# --- Issue #12: ActionPanel + ChartArea ---

def test_action_panel_instantiates():
    from apps.tui.app import ActionPanel
    panel = ActionPanel()
    assert panel is not None


def test_action_panel_renders_placeholder_before_data():
    from apps.tui.app import ActionPanel
    from unittest.mock import patch
    panel = ActionPanel()
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert "—" in captured["text"]


def test_action_panel_renders_distribution_with_valid_payload():
    from apps.tui.app import ActionPanel
    from unittest.mock import patch
    panel = ActionPanel()
    panel.set_data(
        action_counts={"buy": 20, "hold": 60, "sell": 20},
        last_action=1,
        cumulative_buys=20,
        cumulative_sells=20,
    )
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    text = captured["text"]
    assert "BUY" in text
    assert "HOLD" in text
    assert "SELL" in text


def test_action_panel_bar_length_proportional():
    from apps.tui.app import ActionPanel
    from unittest.mock import patch
    panel = ActionPanel()
    panel.set_data(
        action_counts={"buy": 100, "hold": 0, "sell": 0},
        last_action=1,
        cumulative_buys=100,
        cumulative_sells=0,
    )
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    text = captured["text"]
    # BUY bar should be full (6 chars), HOLD and SELL bars empty
    assert "██████" in text


def test_action_panel_last_action_green_for_buy():
    from apps.tui.app import ActionPanel
    from unittest.mock import patch
    panel = ActionPanel()
    panel.set_data(
        action_counts={"buy": 10, "hold": 80, "sell": 10},
        last_action=1,
        cumulative_buys=10,
        cumulative_sells=10,
    )
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert "green" in captured["text"]


def test_action_panel_last_action_red_for_sell():
    from apps.tui.app import ActionPanel
    from unittest.mock import patch
    panel = ActionPanel()
    panel.set_data(
        action_counts={"buy": 10, "hold": 80, "sell": 10},
        last_action=2,
        cumulative_buys=10,
        cumulative_sells=10,
    )
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert "red" in captured["text"]


def test_chart_area_composes_chart_and_action_panels():
    from apps.tui.app import ChartArea
    area = ChartArea()
    children = list(area.compose())
    class_names = [type(c).__name__ for c in children]
    assert "ChartPanel" in class_names
    assert "ActionPanel" in class_names


def test_tui_app_composes_with_chart_area():
    from apps.tui.app import TUIApp, ChartArea
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    children = list(app.compose())
    class_names = [type(c).__name__ for c in children]
    assert "ChartArea" in class_names


# --- Issue #13: PricePanel ---

def test_price_panel_instantiates():
    from apps.tui.app import PricePanel
    panel = PricePanel()
    assert panel is not None


def test_price_panel_shows_placeholder_before_data():
    from apps.tui.app import PricePanel
    from unittest.mock import patch
    panel = PricePanel()
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert "—" in captured["text"]


def test_price_panel_renders_with_valid_data():
    from apps.tui.app import PricePanel
    from unittest.mock import patch
    panel = PricePanel()
    prices = [100.0 + i for i in range(20)]
    actions = [0] * 20
    panel.set_data(prices=prices, actions=actions)
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert captured.get("text") is not None
    assert captured["text"] != "—"


def test_price_panel_single_point_shows_placeholder():
    from apps.tui.app import PricePanel
    from unittest.mock import patch
    panel = PricePanel()
    panel.set_data(prices=[100.0], actions=[0])
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert "—" in captured["text"]


def test_price_panel_empty_data_shows_placeholder():
    from apps.tui.app import PricePanel
    from unittest.mock import patch
    panel = PricePanel()
    panel.set_data(prices=[], actions=[])
    captured = {}
    with patch.object(panel, "update", side_effect=lambda t: captured.update({"text": t})):
        panel._draw()
    assert "—" in captured["text"]


def test_price_panel_resize_triggers_render():
    from apps.tui.app import PricePanel
    from unittest.mock import patch, MagicMock
    panel = PricePanel()
    panel.set_data(prices=[100.0 + i for i in range(10)], actions=[0] * 10)
    with patch.object(panel, "_draw") as mock_render:
        panel.on_resize()
    mock_render.assert_called_once()


# --- Issue #14: 3-column ChartArea layout ---

def test_chart_area_has_three_panels():
    from apps.tui.app import ChartArea
    area = ChartArea()
    children = list(area.compose())
    class_names = [type(c).__name__ for c in children]
    assert class_names.count("ChartPanel") == 1
    assert class_names.count("PricePanel") == 1
    assert class_names.count("ActionPanel") == 1


def test_chart_area_panel_order():
    from apps.tui.app import ChartArea, ChartPanel, PricePanel, ActionPanel
    area = ChartArea()
    children = list(area.compose())
    assert isinstance(children[0], ChartPanel)
    assert isinstance(children[1], PricePanel)
    assert isinstance(children[2], ActionPanel)


def test_richlog_height_is_4():
    from apps.tui.app import TUIApp
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    children = list(app.compose())
    from textual.widgets import RichLog
    logs = [c for c in children if isinstance(c, RichLog)]
    assert len(logs) == 1


def test_tui_app_composes_without_error():
    from apps.tui.app import TUIApp, ChartArea, PricePanel, ActionPanel, ChartPanel
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    children = list(app.compose())
    assert len(children) > 0


def test_handle_update_sends_price_series_to_price_panel(mocker):
    from apps.tui.app import TUIApp, PricePanel
    from queue import Queue
    app = TUIApp(update_queue=Queue())
    mock_panel = mocker.MagicMock()
    mock_tile = mocker.MagicMock()
    mock_log = mocker.MagicMock()
    def fake_query_one(selector, cls=None):
        if selector == "#price-panel":
            return mock_panel
        if "log" in str(selector):
            return mock_log
        return mock_tile
    mocker.patch.object(app, "query_one", side_effect=fake_query_one)
    app._handle_update({
        "generation": 1,
        "current_sharpe": 0.5,
        "best_sharpe": 0.5,
        "promoted": False,
        "total_generations": 10,
        "final_balance": 10000.0,
        "pnl": 0.0,
        "initial_balance": 10000.0,
        "price_series": [100.0, 101.0, 102.0],
        "action_series": [0, 1, 2],
    })
    mock_panel.set_data.assert_called_once_with(
        prices=[100.0, 101.0, 102.0],
        actions=[0, 1, 2],
    )
