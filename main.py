import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description='TradingZero web backend')
    parser.add_argument('--host', default='0.0.0.0', help='Host for Uvicorn server')
    parser.add_argument('--port', type=int, default=8000, help='Port for Uvicorn server')
    parser.add_argument('--reload', action='store_true', help='Enable auto reload for local development')
    args = parser.parse_args()

    uvicorn.run(
        'backend.app:app',
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == '__main__':
    main()
