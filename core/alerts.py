"""Webhook alert dispatcher — Telegram, Discord, and Slack notifications."""

import json
import time
from pathlib import Path
from datetime import datetime

try:
    from urllib.request import Request, urlopen
    from urllib.error import URLError

    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "webhooks.json"


def _load_config() -> dict:
    CONFIG_PATH.parent.mkdir(exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return {"telegram": {}, "discord": {}, "slack": {}}


def _save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def configure_telegram(bot_token: str, chat_id: str):
    cfg = _load_config()
    cfg["telegram"] = {"bot_token": bot_token, "chat_id": chat_id}
    _save_config(cfg)


def configure_discord(webhook_url: str):
    cfg = _load_config()
    cfg["discord"] = {"webhook_url": webhook_url}
    _save_config(cfg)


def configure_slack(webhook_url: str):
    cfg = _load_config()
    cfg["slack"] = {"webhook_url": webhook_url}
    _save_config(cfg)


def _send_telegram(message: str, config: dict) -> bool:
    bot_token = config.get("bot_token", "")
    chat_id = config.get("chat_id", "")
    if not bot_token or not chat_id:
        return False
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode()
    req = Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urlopen(req, timeout=15)
        return True
    except URLError:
        return False


def _send_discord(message: str, config: dict) -> bool:
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        return False
    payload = json.dumps(
        {
            "content": message,
            "username": "Angetic Essence",
        }
    ).encode()
    req = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urlopen(req, timeout=15)
        return True
    except URLError:
        return False


def _send_slack(message: str, config: dict) -> bool:
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        return False
    payload = json.dumps({"text": message}).encode()
    req = Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urlopen(req, timeout=15)
        return True
    except URLError:
        return False


def send_alert(title: str, description: str, fields: dict = None) -> dict:
    results = {}
    cfg = _load_config()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    lines = [f"<b>{title}</b>", f"{description}", f"<i>{timestamp}</i>"]
    if fields:
        for k, v in fields.items():
            lines.append(f"{k}: {v}")
    message = "\n".join(lines)

    for channel, channel_config in cfg.items():
        if not channel_config:
            continue
        if channel == "telegram":
            results["telegram"] = _send_telegram(message, channel_config)
        elif channel == "discord":
            results["discord"] = _send_discord(message, channel_config)
        elif channel == "slack":
            results["slack"] = _send_slack(message, channel_config)

    return results


def notify_task_complete(agent_name: str, task: str, duration_minutes: float):
    return send_alert(
        title=f"Agent Complete: {agent_name}",
        description=f"Finished task in {duration_minutes:.1f}m",
        fields={"Task": task[:200], "Agent": agent_name},
    )


def notify_penetration_test(result: dict):
    return send_alert(
        title="Penetration Test Result",
        description=result.get("summary", "No summary provided"),
        fields={
            "Target": result.get("target", "unknown"),
            "Findings": str(result.get("findings_count", 0)),
            "Severity": result.get("severity", "info"),
        },
    )


def notify_evolution_cycle(generation: int, changes: list[str]):
    return send_alert(
        title=f"Evolution Cycle #{generation}",
        description=f"{len(changes)} changes applied",
        fields={f"Change {i + 1}": c[:100] for i, c in enumerate(changes)},
    )
