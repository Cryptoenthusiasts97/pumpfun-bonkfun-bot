#!/usr/bin/env python3
"""
trade.py — compatibility wrapper implementing legacy CLI flags
Writes a temp bot YAML to bots/trade-cli.yaml then launches the existing bot_runner.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path.cwd()
BOTS_DIR = ROOT / "bots"
DEFAULT_BASE = BOTS_DIR / "bot-sniper-2-logs.yaml"
OUT_PATH = BOTS_DIR / "trade-cli.yaml"
BACKUP_PATH = BOTS_DIR / "trade-cli.yaml.bak"

def load_base_yaml(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def ensure_bots_dir():
    BOTS_DIR.mkdir(parents=True, exist_ok=True)

def build_config_from_flags(base: dict, args: argparse.Namespace) -> dict:
    cfg = base.copy()

    # Basic metadata
    cfg.setdefault("name", "trade-cli")
    cfg["enabled"] = True
    cfg.setdefault("separate_process", False)

    # Ensure expected sections exist
    cfg.setdefault("trade", {})
    cfg.setdefault("filters", {})
    cfg.setdefault("retries", {})

    # Apply flags
    if args.yolo:
        cfg["filters"]["yolo_mode"] = True
        # for YOLO behavior match the docs: short hold
        cfg["trade"]["exit_strategy"] = "time_based"
        cfg["retries"]["wait_after_buy"] = args.wait_after_buy or 20

    if args.marry:
        cfg["filters"]["marry_mode"] = True
        cfg["filters"]["yolo_mode"] = False  # marry implies accumulation

    if args.match:
        cfg["filters"]["match_string"] = args.match

    if args.bro:
        cfg["filters"]["bro_address"] = args.bro

    if args.buy_amount is not None:
        cfg["trade"]["buy_amount"] = args.buy_amount

    if args.listener:
        cfg["filters"]["listener_type"] = args.listener

    # Respect existing env_file / rpc / wss entries in base, do not write keys here.
    cfg.setdefault("env_file", ".env")

    return cfg

def write_config(cfg: dict, out: Path):
    if out.exists():
        shutil.copy2(out, BACKUP_PATH)
    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    print(f"Wrote config to {out} (backup at {BACKUP_PATH} if existed)")

def run_bot_runner():
    # Prefer uv run if available (repo uses uv), fallback to python
    cmd = None
    if shutil.which("uv"):
        cmd = ["uv", "run", "src/bot_runner.py"]
    else:
        # try running with same Python interpreter
        cmd = [sys.executable, "src/bot_runner.py"]

    print(f"Launching bot runner: {' '.join(cmd)}")
    return subprocess.call(cmd)

def parse_args():
    p = argparse.ArgumentParser(description="Legacy trade.py wrapper for pumpfun-bonkfun-bot")
    p.add_argument("--yolo", action="store_true", help="Continuous YOLO trading (short hold)")
    p.add_argument("--match", type=str, help="Only trade tokens matching this string")
    p.add_argument("--bro", type=str, help="Only trade tokens created by this address")
    p.add_argument("--marry", action="store_true", help="Buy and never sell (accumulation)")
    p.add_argument("--buy-amount", dest="buy_amount", type=float, help="SOL amount to spend per buy")
    p.add_argument("--listener", choices=["logs", "blocks", "geyser", "pumpportal"], help="Listener type")
    p.add_argument("--base", type=str, help="Base YAML to use (defaults to bots/bot-sniper-2-logs.yaml)")
    p.add_argument("--wait-after-buy", dest="wait_after_buy", type=int, help="Hold seconds after buy (YOLO)")
    return p.parse_args()

def main():
    args = parse_args()
    ensure_bots_dir()

    base_path = Path(args.base) if args.base else DEFAULT_BASE
    base = load_base_yaml(base_path)

    cfg = build_config_from_flags(base, args)
    write_config(cfg, OUT_PATH)

    rc = run_bot_runner()
    if rc != 0:
        print(f"Bot runner exited with code {rc}", file=sys.stderr)
        sys.exit(rc)

if __name__ == "__main__":
    main()