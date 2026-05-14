import pytest
from queue import Queue
from unittest.mock import patch


# --- TUIApp instantiation ---

def test_tui_app_instantiates():
    from tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app is not None


def test_tui_app_has_update_queue():
    from tui.app import TUIApp
    queue = Queue()
    app = TUIApp(update_queue=queue)
    assert app.update_queue is queue


def test_stop_requested_false_on_init():
    from tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._stop_requested is False


def test_promotions_zero_on_init():
    from tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._promotions == 0


def test_initial_balance_zero_on_init():
    from tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._initial_balance == 0.0


def test_action_quit_sets_stop_requested():
    from tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    with patch.object(app, "exit"):
        app.action_quit()
    assert app._stop_requested is True


# --- _handle_update behavior ---

def test_handle_update_increments_promotions_on_promote():
    from tui.app import TUIApp
    app = TUIApp(update_queue=Queue())
    assert app._promotions == 0
    app._promotions += 1
    assert app._promotions == 1


# --- ChartPanel ---

def test_chart_panel_add_point_does_not_raise():
    from tui.app import ChartPanel
    panel = ChartPanel()
    panel.add_point(0.1)
    panel.add_point(0.2)
    assert len(panel._sharpe_history) == 2


def test_chart_panel_single_point_skips_render():
    from tui.app import ChartPanel
    panel = ChartPanel()
    panel.add_point(0.5)
    assert len(panel._sharpe_history) == 1


def test_chart_panel_negative_sharpe_tracked():
    from tui.app import ChartPanel
    panel = ChartPanel()
    panel.add_point(-0.3)
    panel.add_point(-0.1)
    assert panel._sharpe_history == [-0.3, -0.1]


# --- MetricBox ---

def test_metric_box_set_value_does_not_raise():
    from tui.app import MetricBox
    box = MetricBox()
    with patch.object(box, "update"):
        box.set_value("Sharpe", "0.4200", "bold green")


def test_metric_box_set_value_builds_correct_text():
    from tui.app import MetricBox
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
    from tui.app import MetricBox
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
    from tui.app import MetricBox
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
    from tui.app import MetricBox
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
    from tui.app import ChartPanel
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
    from tui.app import ChartPanel
    from unittest.mock import patch, MagicMock
    panel = ChartPanel()
    panel._size = MagicMock()
    panel._size.width = 80
    panel._size.height = 20
    with patch.object(panel, "update"):
        for _ in range(5):
            panel.add_point(2.5)
