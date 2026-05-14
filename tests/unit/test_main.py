def test_main_starts_uvicorn_web_server(mocker):
    import main

    run_mock = mocker.patch('main.uvicorn.run')
    mocker.patch('sys.argv', ['main.py'])

    main.main()

    run_mock.assert_called_once_with(
        'backend.app:app',
        host='0.0.0.0',
        port=8000,
        reload=False,
    )


def test_main_accepts_host_port_reload_flags(mocker):
    import main

    run_mock = mocker.patch('main.uvicorn.run')
    mocker.patch('sys.argv', ['main.py', '--host', '127.0.0.1', '--port', '9000', '--reload'])

    main.main()

    run_mock.assert_called_once_with(
        'backend.app:app',
        host='127.0.0.1',
        port=9000,
        reload=True,
    )
