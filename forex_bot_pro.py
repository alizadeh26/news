import argparse
import json
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


DB_PATH = os.getenv("DB_PATH", "forex_events.db")
FOREX_FACTORY_MONTH_URL = os.getenv("FOREX_FACTORY_MONTH_URL", "https://www.forexfactory.com/calendar")
FOREX_FACTORY_TIMEZONE = os.getenv("FOREX_FACTORY_TIMEZONE", "America/New_York")
TARGET_TIMEZONE = os.getenv("TARGET_TIMEZONE", "UTC")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
ALERT_BEFORE_MINUTES = int(os.getenv("ALERT_BEFORE_MINUTES", "10"))
PREPARE_BEFORE_MINUTES = int(os.getenv("PREPARE_BEFORE_MINUTES", "60"))
TARGET_CURRENCIES = set(os.getenv("TARGET_CURRENCIES", "USD,EUR,GBP").split(","))
TARGET_IMPACTS = set(os.getenv("TARGET_IMPACTS", "Medium,High").split(","))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_OFFSET_FILE = os.getenv("TELEGRAM_OFFSET_FILE", "telegram_offset.txt")
HEADERS = {
    "User-Agent": os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    )
}

KEYWORDS_WEIGHTS = {
    "interest rate": 8,
    "rate statement": 8,
    "fomc": 8,
    "ecb": 8,
    "boe": 8,
    "cpi": 8,
    "inflation": 8,
    "nfp": 8,
    "non-farm": 8,
    "gdp": 6,
    "pmi": 6,
    "employment": 6,
    "unemployment": 6,
    "retail sales": 4,
    "speech": 3,
}

TIER1_KEYWORDS = {
    "interest rate",
    "rate statement",
    "fomc",
    "ecb",
    "boe",
    "cpi",
    "inflation",
    "nfp",
    "non-farm",
}

TIER2_KEYWORDS = {
    "gdp",
    "pmi",
    "employment",
    "unemployment",
}

TIER3_KEYWORDS = {
    "retail sales",
    "speech",
}


@dataclass
class Event:
    source_id: str
    title: str
    currency: str
    impact: str
    event_time_utc: str
    month_key: str
    raw_text: str


def log(message: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {message}")


def require_env() -> None:
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            source_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            currency TEXT NOT NULL,
            impact TEXT NOT NULL,
            event_time_utc TEXT NOT NULL,
            month_key TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            analysis_sent_at TEXT,
            final_alert_sent_at TEXT,
            last_seen_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_calendar_html() -> str:
    response = requests.get(FOREX_FACTORY_MONTH_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def infer_impact_from_cell(cell) -> str:
    if cell is None:
        return "Low"

    html = str(cell).lower()
    title = (cell.get("title") or "").lower() if hasattr(cell, "get") else ""
    classes = " ".join(cell.get("class", [])) if hasattr(cell, "get") else ""
    lowered = f"{html} {title} {classes}".lower()

    if any(token in lowered for token in ["high", "icon--ff-impact-red", "impact--high", "calendar__impact--high"]):
        return "High"
    if any(token in lowered for token in ["medium", "med", "icon--ff-impact-ora", "impact--medium", "calendar__impact--medium"]):
        return "Medium"
    return "Low"


def extract_text_by_selectors(row, selectors: List[str]) -> str:
    for selector in selectors:
        cell = row.select_one(selector)
        if cell:
            text = " ".join(cell.stripped_strings).strip()
            if text:
                return text
    return ""


def parse_calendar_datetime(date_text: str, time_text: str, base_year: int) -> Optional[datetime]:
    if not date_text or not time_text:
        return None

    date_text = re.sub(r"\s+", " ", date_text.strip())
    time_text = re.sub(r"\s+", "", time_text.strip().lower())

    if any(token in time_text for token in ["all day", "tentative", "day"]):
        return None

    source_tz = ZoneInfo(FOREX_FACTORY_TIMEZONE)
    target_tz = ZoneInfo(TARGET_TIMEZONE)

    date_formats = [
        "%a %b %d %Y",
        "%b %d %Y",
        "%a%b %d %Y",
        "%a %b %d",
        "%b %d",
    ]
    time_formats = ["%I:%M%p", "%H:%M"]

    candidates = []
    for df in date_formats:
        for tf in time_formats:
            try:
                if "%Y" in df:
                    raw = f"{date_text} {time_text}"
                    fmt = f"{df} {tf}"
                else:
                    raw = f"{date_text} {base_year} {time_text}"
                    fmt = f"{df} %Y {tf}"
                parsed = datetime.strptime(raw, fmt).replace(tzinfo=source_tz)
                candidates.append(parsed)
            except Exception:
                continue

    if not candidates:
        return None

    now_source = datetime.now(source_tz)
    best = min(candidates, key=lambda dt: abs((dt - now_source).total_seconds()))

    if best.month == 12 and now_source.month == 1:
        best = best.replace(year=now_source.year - 1)
    elif best.month == 1 and now_source.month == 12:
        best = best.replace(year=now_source.year + 1)

    return best.astimezone(target_tz)


def impact_rank(impact: str) -> int:
    # Higher is more important
    if impact == "High":
        return 3
    if impact == "Medium":
        return 2
    return 1


def normalize_title(title: str) -> str:
    # Basic normalization to reduce accidental duplicates
    t = title.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def parse_calendar(html: str, month_key: str) -> List[Event]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.calendar__table")
    if not table:
        log("Calendar table not found")
        return []

    rows = table.select("tr.calendar__row, tr[class*='calendar__row']")
    if not rows:
        rows = table.find_all("tr")

    now_utc = datetime.now(timezone.utc)
    current_date_text = ""

    # Dedup map: (currency, normalized_title, event_time_iso) -> Event
    dedup: dict[tuple[str, str, str], Event] = {}

    for row in rows:
        row_classes = " ".join(row.get("class", []))
        if "calendar__row--grey" in row_classes:
            continue

        date_text = extract_text_by_selectors(
            row,
            [
                "td.calendar__cell.calendar__date",
                "td.calendar__date",
                "td[class*='date']",
            ],
        )
        if date_text:
            current_date_text = date_text

        time_text = extract_text_by_selectors(
            row,
            [
                "td.calendar__cell.calendar__time",
                "td.calendar__time",
                "td[class*='time']",
            ],
        )
        currency = extract_text_by_selectors(
            row,
            [
                "td.calendar__cell.calendar__currency",
                "td.calendar__currency",
                "td[class*='currency']",
            ],
        )
        title = extract_text_by_selectors(
            row,
            [
                "td.calendar__cell.calendar__event",
                "td.calendar__event",
                "td[class*='event']",
            ],
        )

        impact_cell = None
        for selector in [
            "td.calendar__cell.calendar__impact",
            "td.calendar__impact",
            "td[class*='impact']",
        ]:
            impact_cell = row.select_one(selector)
            if impact_cell:
                break

        impact = infer_impact_from_cell(impact_cell)

        if not currency or currency not in TARGET_CURRENCIES:
            continue
        if not title:
            continue
        if impact not in TARGET_IMPACTS:
            continue
        if not current_date_text or not time_text:
            continue

        event_dt = parse_calendar_datetime(current_date_text, time_text, now_utc.year)
        if not event_dt:
            continue

        raw_text = " ".join(row.stripped_strings)
        event_time_iso = event_dt.isoformat()

        norm_title = normalize_title(title)
        key = (currency, norm_title, event_time_iso)

        candidate = Event(
            source_id=f"{currency}|{impact}|{title}|{event_time_iso}",
            title=title,
            currency=currency,
            impact=impact,
            event_time_utc=event_time_iso,
            month_key=month_key,
            raw_text=raw_text,
        )

        existing = dedup.get(key)
        if existing is None:
            dedup[key] = candidate
        else:
            # Keep the one with higher impact if there is any difference
            if impact_rank(candidate.impact) > impact_rank(existing.impact):
                dedup[key] = candidate

    events = list(dedup.values())
    events.sort(key=lambda e: e.event_time_utc)
    return events


def upsert_events(events: List[Event]) -> int:
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    count = 0

    for event in events:
        cur.execute(
            """
            INSERT INTO events (
                source_id, title, currency, impact, event_time_utc, month_key, raw_text,
                analysis_sent_at, final_alert_sent_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                title=excluded.title,
                currency=excluded.currency,
                impact=excluded.impact,
                event_time_utc=excluded.event_time_utc,
                month_key=excluded.month_key,
                raw_text=excluded.raw_text,
                last_seen_at=excluded.last_seen_at
            """,
            (
                event.source_id,
                event.title,
                event.currency,
                event.impact,
                event.event_time_utc,
                event.month_key,
                event.raw_text,
                now,
            ),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def classify_event_tier(title: str) -> str:
    lowered = title.lower()
    if any(keyword in lowered for keyword in TIER1_KEYWORDS):
        return "Tier 1"
    if any(keyword in lowered for keyword in TIER2_KEYWORDS):
        return "Tier 2"
    if any(keyword in lowered for keyword in TIER3_KEYWORDS):
        return "Tier 3"
    return "General"


def event_weight(title: str, impact: str) -> int:
    score = 5
    lowered = title.lower()
    for keyword, weight in KEYWORDS_WEIGHTS.items():
        if keyword in lowered:
            score += weight
    if impact == "High":
        score += 12
    elif impact == "Medium":
        score += 6
    return score


def confidence_score(title: str, impact: str, stage: str) -> int:
    score = event_weight(title, impact)
    tier = classify_event_tier(title)

    if tier == "Tier 1":
        score += 15
    elif tier == "Tier 2":
        score += 8
    elif tier == "Tier 3":
        score += 3

    if stage == "final":
        score += 5

    return max(0, min(score, 100))


def bias_strength(confidence: int) -> str:
    if confidence >= 80:
        return "Strong"
    if confidence >= 60:
        return "Moderate"
    return "Mild"


def map_pair_bias(currency: str, confidence: int) -> List[str]:
    strength = bias_strength(confidence)

    if currency == "USD":
        return [
            f"DXY: bullish {strength.lower()} bias if USD expectations strengthen",
            f"EURUSD: bearish {strength.lower()} bias under USD strength scenario",
            f"GBPUSD: bearish {strength.lower()} bias under USD strength scenario",
        ]
    if currency == "EUR":
        return [
            f"EURUSD: bullish {strength.lower()} bias if release supports EUR strength",
            f"DXY: bearish mild-to-{strength.lower()} pressure if EUR strengthens broadly",
            "GBPUSD: mostly indirect effect unless USD reprices at the same time",
        ]
    if currency == "GBP":
        return [
            f"GBPUSD: bullish {strength.lower()} bias if release supports GBP strength",
            "DXY: mostly indirect effect unless USD also reprices",
            "EURUSD: limited direct impact unless broader Europe/UK macro repricing occurs",
        ]
    return ["No specific pair mapping available"]


def build_analysis(title: str, currency: str, impact: str, event_time_utc: str, stage: str) -> str:
    score = event_weight(title, impact)
    tier = classify_event_tier(title)
    confidence = confidence_score(title, impact, stage)
    strength = bias_strength(confidence)
    scenarios = map_pair_bias(currency, confidence)

    reasons = [
        f"Currency in focus: {currency}",
        f"Impact level: {impact}",
        f"Event tier: {tier}",
        f"Sensitivity score: {score}",
        f"Confidence score: {confidence}/100",
        f"Bias strength: {strength}",
        f"Stage: {stage}",
    ]

    event_dt_utc = datetime.fromisoformat(event_time_utc)
    event_dt_ny = event_dt_utc.astimezone(ZoneInfo(FOREX_FACTORY_TIMEZONE))

    prefix = "Preparation alert" if stage == "prepare" else "Final pre-news alert"
    lines = [
        prefix,
        "",
        f"Event: {title}",
        f"Time (UTC): {event_dt_utc.strftime('%Y-%m-%d %H:%M UTC')}",
        f"Time (New York): {event_dt_ny.strftime('%Y-%m-%d %I:%M %p %Z')}",
        f"Currency: {currency}",
        f"Impact: {impact}",
        f"Confidence: {confidence}/100",
        f"Bias strength: {strength}",
        "",
        "Scenarios:",
    ]
    lines.extend([f"- {item}" for item in scenarios])
    lines.append("")
    lines.append("Reasoning:")
    lines.extend([f"- {item}" for item in reasons])
    return "\n".join(lines)


def send_telegram_message(text: str, chat_id: Optional[str] = None) -> dict:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id or TELEGRAM_CHAT_ID, "text": text}
    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def get_telegram_updates(offset: Optional[int] = None) -> dict:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 10}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def month_key_for_now() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-{now.month:02d}"


def monthly_sync() -> None:
    init_db()
    html = fetch_calendar_html()
    month_key = month_key_for_now()
    events = parse_calendar(html, month_key)
    count = upsert_events(events)
    log(f"Monthly sync finished. Upserted {count} events for {month_key}")


def weekly_refresh() -> None:
    init_db()
    html = fetch_calendar_html()
    month_key = month_key_for_now()
    events = parse_calendar(html, month_key)
    count = upsert_events(events)
    log(f"Weekly refresh finished. Refreshed {count} events for {month_key}")


def mark_analysis_sent(source_id: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE events SET analysis_sent_at = ? WHERE source_id = ?",
        (datetime.now(timezone.utc).isoformat(), source_id),
    )
    conn.commit()
    conn.close()


def mark_final_sent(source_id: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE events SET final_alert_sent_at = ? WHERE source_id = ?",
        (datetime.now(timezone.utc).isoformat(), source_id),
    )
    conn.commit()
    conn.close()


def dispatcher() -> None:
    require_env()
    init_db()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT source_id, title, currency, impact, event_time_utc, analysis_sent_at, final_alert_sent_at FROM events"
    )
    rows = cur.fetchall()
    conn.close()

    now = datetime.now(timezone.utc)

    for row in rows:
        source_id, title, currency, impact, event_time_utc, analysis_sent_at, final_alert_sent_at = row
        event_dt = datetime.fromisoformat(event_time_utc)
        seconds_to_event = (event_dt - now).total_seconds()

        prepare_window_low = (PREPARE_BEFORE_MINUTES * 60) - 300
        prepare_window_high = PREPARE_BEFORE_MINUTES * 60
        final_window_low = (ALERT_BEFORE_MINUTES * 60) - 300
        final_window_high = ALERT_BEFORE_MINUTES * 60

        if analysis_sent_at is None and prepare_window_low <= seconds_to_event <= prepare_window_high:
            text = build_analysis(title, currency, impact, event_time_utc, stage="prepare")
            send_telegram_message(text)
            mark_analysis_sent(source_id)
            log(f"Preparation alert sent: {source_id}")

        if final_alert_sent_at is None and final_window_low <= seconds_to_event <= final_window_high:
            text = build_analysis(title, currency, impact, event_time_utc, stage="final")
            send_telegram_message(text)
            mark_final_sent(source_id)
            log(f"Final alert sent: {source_id}")


def get_next_events(limit: int = 5) -> List[sqlite3.Row]:
    init_db()
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_id, title, currency, impact, event_time_utc, analysis_sent_at, final_alert_sent_at
        FROM events
        WHERE event_time_utc >= ?
        ORDER BY event_time_utc ASC
        LIMIT ?
        """,
        (datetime.now(timezone.utc).isoformat(), limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def build_status_message() -> str:
    upcoming = get_next_events(limit=3)
    lines = [
        "Forex bot status",
        "",
        f"Current UTC time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Current New York time: {datetime.now(ZoneInfo(FOREX_FACTORY_TIMEZONE)).strftime('%Y-%m-%d %I:%M %p %Z')}",
        "",
    ]

    if not upcoming:
        lines.append("No upcoming events found in the database.")
        return "\n".join(lines)

    lines.append("Next events:")
    for row in upcoming:
        event_dt_utc = datetime.fromisoformat(row["event_time_utc"])
        event_dt_ny = event_dt_utc.astimezone(ZoneInfo(FOREX_FACTORY_TIMEZONE))
        lines.append(
            f"- {row['currency']} | {row['impact']} | {row['title']} | "
            f"UTC {event_dt_utc.strftime('%Y-%m-%d %H:%M')} | "
            f"NY {event_dt_ny.strftime('%Y-%m-%d %I:%M %p %Z')}"
        )
    return "\n".join(lines)


def build_nextnews_message() -> str:
    upcoming = get_next_events(limit=5)
    if not upcoming:
        return "No upcoming events found."

    lines = ["Next scheduled news events", ""]
    for row in upcoming:
        event_dt_utc = datetime.fromisoformat(row["event_time_utc"])
        event_dt_ny = event_dt_utc.astimezone(ZoneInfo(FOREX_FACTORY_TIMEZONE))
        lines.extend(
            [
                f"Event: {row['title']}",
                f"Currency: {row['currency']}",
                f"Impact: {row['impact']}",
                f"Time (UTC): {event_dt_utc.strftime('%Y-%m-%d %H:%M UTC')}",
                f"Time (New York): {event_dt_ny.strftime('%Y-%m-%d %I:%M %p %Z')}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_today_message() -> str:
    init_db()
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    ny_tz = ZoneInfo(FOREX_FACTORY_TIMEZONE)
    now_ny = datetime.now(ny_tz)
    start_ny = now_ny.replace(hour=0, minute=0, second=0, microsecond=0)
    end_ny = now_ny.replace(hour=23, minute=59, second=59, microsecond=999999)

    start_utc = start_ny.astimezone(timezone.utc).isoformat()
    end_utc = end_ny.astimezone(timezone.utc).isoformat()

    cur.execute(
        """
        SELECT source_id, title, currency, impact, event_time_utc
        FROM events
        WHERE event_time_utc >= ? AND event_time_utc <= ?
        ORDER BY event_time_utc ASC
        """,
        (start_utc, end_utc),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No scheduled news events found for today."

    lines = [
        f"Today's scheduled news events ({now_ny.strftime('%Y-%m-%d')} New York)",
        "",
    ]

    for row in rows:
        event_dt_utc = datetime.fromisoformat(row["event_time_utc"])
        event_dt_ny = event_dt_utc.astimezone(ny_tz)
        lines.extend(
            [
                f"Event: {row['title']}",
                f"Currency: {row['currency']}",
                f"Impact: {row['impact']}",
                f"Time (UTC): {event_dt_utc.strftime('%Y-%m-%d %H:%M UTC')}",
                f"Time (New York): {event_dt_ny.strftime('%Y-%m-%d %I:%M %p %Z')}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def process_telegram_commands() -> None:
    require_env()
    init_db()

    offset = None
    if os.path.exists(TELEGRAM_OFFSET_FILE):
        with open(TELEGRAM_OFFSET_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if raw.isdigit():
                offset = int(raw)

    updates = get_telegram_updates(offset=offset)
    for item in updates.get("result", []):
        update_id = item.get("update_id")
        message = item.get("message", {})
        text = (message.get("text") or "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))

        if not text or not chat_id:
            continue

        command = text.split()[0].lower()

        if command == "/status":
            send_telegram_message(build_status_message(), chat_id=chat_id)
        elif command == "/nextnews":
            send_telegram_message(build_nextnews_message(), chat_id=chat_id)
        elif command == "/today":
            send_telegram_message(build_today_message(), chat_id=chat_id)
        elif command == "/start":
            send_telegram_message(
                "Forex bot is active. Available commands:\n/start\n/status\n/nextnews\n/today",
                chat_id=chat_id,
            )

        if update_id is not None:
            offset = update_id + 1

    if offset is not None:
        with open(TELEGRAM_OFFSET_FILE, "w", encoding="utf-8") as f:
            f.write(str(offset))


def export_events_json(output_path: str = "events_export.json") -> None:
    init_db()
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY event_time_utc ASC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    log(f"Exported {len(rows)} events to {output_path}")


def github_actions_auto_commit() -> None:
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        return
    if os.getenv("GIT_AUTO_COMMIT", "false").lower() != "true":
        return

    try:
        subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(
            [
                "git",
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            ],
            check=True,
        )

        paths_to_add = []
        if os.path.exists(DB_PATH):
            paths_to_add.append(DB_PATH)
        else:
            log(f"DB file not found (skipping add): {DB_PATH}")

        if os.path.exists(TELEGRAM_OFFSET_FILE):
            paths_to_add.append(TELEGRAM_OFFSET_FILE)
        else:
            log(f"Offset file not found (skipping add): {TELEGRAM_OFFSET_FILE}")

        if not paths_to_add:
            log("No state files found to commit")
            return

        subprocess.run(["git", "add", *paths_to_add], check=True)
        diff_result = subprocess.run(["git", "diff", "--cached", "--quiet"], check=False)
        if diff_result.returncode == 0:
            log("No state changes to commit")
            return

        subprocess.run(["git", "commit", "-m", "Update forex bot state"], check=True)
        subprocess.run(["git", "push"], check=True)
        log("State changes committed and pushed")
    except Exception as exc:
        log(f"Git auto-commit skipped or failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Forex Factory monthly bot")
    parser.add_argument(
        "command",
        choices=["monthly-sync", "weekly-refresh", "dispatch", "export-json", "telegram-commands"],
    )
    parser.add_argument("--output", default="events_export.json")
    args = parser.parse_args()

    if args.command == "monthly-sync":
        monthly_sync()
        github_actions_auto_commit()
    elif args.command == "weekly-refresh":
        weekly_refresh()
        github_actions_auto_commit()
    elif args.command == "dispatch":
        dispatcher()
        github_actions_auto_commit()
    elif args.command == "export-json":
        export_events_json(args.output)
    elif args.command == "telegram-commands":
        process_telegram_commands()
        github_actions_auto_commit()


if __name__ == "__main__":
    main()
