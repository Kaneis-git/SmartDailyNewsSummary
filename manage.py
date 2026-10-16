"""共用命令入口：在项目根运行 python manage.py api | worker | init-db。"""
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "ai-service")]


def main():
    parser = argparse.ArgumentParser(description="AI Daily News Assistant")
    parser.add_argument("command", choices=["api", "worker", "init-db"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "api":
        import uvicorn
        uvicorn.run("app.main:app", host=args.host, port=args.port)
    elif args.command == "worker":
        from app.worker import run_worker
        run_worker()
    else:
        from app.config import get_settings
        from app.db import make_session_factory, sync_sources
        settings = get_settings()
        sync_sources(make_session_factory(settings.db_url), settings.sources_file)
        print("Database initialized")


if __name__ == "__main__":
    main()
