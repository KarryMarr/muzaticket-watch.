#!/usr/bin/env python3
"""Checks muzaticket widget page and sends a Telegram message when tickets become available."""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://widget.muzaticket.ru/sites/beta/action?skey=160ea02af3df89f4ec416a0741a6325a&id=37402"
STATE_FILE = Path(__file__).with_name("state.json")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_sessions(html):
    sessions = {}
    for card in html.split('class="event-card event-card_list-style')[1:]:
        date = re.search(r'data-i18n-date="([^"]+)"', card)
        time = re.search(r'event-card__time-text">([^<]+)', card)
        count = re.search(r"<span>(\d+)</span>\s*<span data-i18n-ticket", card)
        if date and time and count:
            sessions[f"{date.group(1)} {time.group(1).strip()}"] = int(count.group(1))
    return sessions


def send_telegram(text):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def main():
    if "--test" in sys.argv:
        send_telegram("Муза: тестовое сообщение, бот работает")
        return 0

    try:
        sessions = parse_sessions(fetch(URL))
    except Exception as error:
        print(f"ERROR fetch: {error}")
        return 1

    if not sessions:
        send_telegram(f"Муза: не удалось разобрать страницу, проверь вручную\n{URL}")
        return 1

    available = {key: count for key, count in sessions.items() if count > 0}
    total = sum(available.values())
    print(f"sessions={len(sessions)} available_sessions={len(available)} tickets={total}")

    previous = {}
    if STATE_FILE.exists():
        try:
            previous = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
    STATE_FILE.write_text(json.dumps(available, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if available and available != previous:
        details = "\n".join(f"{key}: {count}" for key, count in sorted(available.items()))
        send_telegram(f"Муза: появились билеты ({total})\n{details}\n{URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
