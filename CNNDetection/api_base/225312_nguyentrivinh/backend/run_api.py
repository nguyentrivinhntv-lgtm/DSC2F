"""
=============================================================================
Script khởi động API Server
=============================================================================
Chạy Uvicorn server cho CNN Detection API.

Usage:
    python run_api.py
    python run_api.py --port 8080
    python run_api.py --reload
"""

import argparse
import os
import sys

import uvicorn


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CNN Detection API Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="Host để bind server."
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", 8000)),
        help="Port để chạy server."
    )
    parser.add_argument(
        "--reload", action="store_true", default=False,
        help="Bật auto-reload khi thay đổi code."
    )
    parser.add_argument(
        "--workers", type=int, default=1,
        help="Số worker processes."
    )
    return parser.parse_args()


def main():
    """Khởi động Uvicorn server."""
    args = parse_args()

    print("=" * 60)
    print("  CNN Detection API Server")
    print(f"  Host   : {args.host}")
    print(f"  Port   : {args.port}")
    print(f"  Reload : {args.reload}")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level="info",
    )


if __name__ == "__main__":
    main()
