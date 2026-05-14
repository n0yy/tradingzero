from queue import Queue


def test_tui_secondary_entrypoint_instantiates_app(mocker):
    from apps.tui.main import main

    run_mock = mocker.patch('apps.tui.main.TUIApp.run')
    queue_mock = mocker.patch('apps.tui.main.Queue', return_value=Queue())

    main()

    queue_mock.assert_called_once()
    run_mock.assert_called_once()
