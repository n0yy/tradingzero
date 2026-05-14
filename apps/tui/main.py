from __future__ import annotations

from queue import Queue

from apps.tui.app import TUIApp


def main() -> None:
    app = TUIApp(update_queue=Queue())
    app.run()


if __name__ == '__main__':
    main()
