"""
Overvåger AccuRanker-søgeord for domænet PengeSparet.dk (domain_id 343517) og sender
en mail via Resend, hvis et søgeord der FØR matchede sin "preferred landing page"
IKKE LÆNGERE matcher.

Alarmen trigges kun ved overgangen "matchede -> matcher ikke længere".
Søgeord der aldrig har haft en preferred URL sat, ignoreres.
Søgeord der allerede ikke matchede sidste gang, giver ikke en ny mail hver dag.

Kører via GitHub Actions (se .github/workflows/preferred-url-check.yml).
"""

import json
import os
import time
import sys

import requests

API_BASE = "https://app.accuranker.com/api/v4"
STATE_FILE = "state.json"

ACCURANKER_API_KEY = os.environ["ACCURANKER_API_KEY"]
RESEND_API_KEY = os.environ["RESEND_API_KEY"]
ALERT_EMAIL_TO = os.environ["ALERT_EMAIL_TO"]
ALERT_EMAIL_FROM = os.environ.get("ALERT_EMAIL_FROM", "onboarding@resend.dev")
DOMAIN_ID = int(os.environ.get("ACCURANKER_DOMAIN_ID", "343517"))

FIELDS = "id,keyword,preferred_landing_page,ranks.landing_page,ranks.created_at"


def fetch_all_keywords():
    """Henter alle søgeord for domænet, med pagination."""
    keywords = []
    limit = 1000
    offset = 0
    headers = {
        "Authorization": f"Token {ACCURANKER_API_KEY}",
        "Content-Type": "application/json",
    }

    while True:
        url = f"{API_BASE}/domains/{DOMAIN_ID}/keywords/"
        params = {"fields": FIELDS, "limit": limit, "offset": offset}
        resp = requests.post(url, headers=headers, params=params, json={}, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        # API'et kan enten returnere en liste direkte eller {"results": [...]}
        batch = data if isinstance(data, list) else data.get("results", [])
        keywords.extend(batch)

        if len(batch) < limit:
            break
        offset += limit
        time.sleep(0.5)  # vær pæn overfor rate-limit (100 req/min)

    return keywords


def get_latest_landing_page_path(keyword_obj):
    """Finder landing page-stien fra det seneste rank-punkt for søgeordet."""
    ranks = keyword_obj.get("ranks") or []
    if not ranks:
        return None
    latest = max(ranks, key=lambda r: r.get("created_at") or "")
    landing_page = latest.get("landing_page")
    return landing_page.get("path") if landing_page else None


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def send_alert_email(regressions):
    lines = []
    for r in regressions:
        current = r["current"] or "(ranker slet ikke)"
        lines.append(f"- \"{r['keyword']}\": preferred = {r['preferred']}  |  ranker nu på = {current}")

    body_text = (
        f"{len(regressions)} søgeord er stoppet med at matche deres preferred URL på PengeSparet.dk:\n\n"
        + "\n".join(lines)
        + "\n\nTjek AccuRanker for detaljer."
    )

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": ALERT_EMAIL_FROM,
            "to": [ALERT_EMAIL_TO],
            "subject": f"AccuRanker: {len(regressions)} preferred URL-mismatch(es)",
            "text": body_text,
        },
        timeout=30,
    )
    resp.raise_for_status()


def main():
    keywords = fetch_all_keywords()
    print(f"Hentede {len(keywords)} søgeord fra AccuRanker.")

    previous_state = load_state()
    is_first_run = len(previous_state) == 0
    new_state = {}
    regressions = []

    for kw in keywords:
        kw_id = str(kw["id"])
        preferred = kw.get("preferred_landing_page")
        preferred_path = preferred.get("path") if preferred else None

        if preferred_path is None:
            # Intet preferred URL sat for dette søgeord - ikke relevant at overvåge
            continue

        current_path = get_latest_landing_page_path(kw)
        currently_matches = current_path == preferred_path

        was_matching = previous_state.get(kw_id)  # True / False / None (ukendt/nyt)

        if was_matching is True and currently_matches is False:
            regressions.append(
                {
                    "keyword": kw["keyword"],
                    "preferred": preferred_path,
                    "current": current_path,
                }
            )

        new_state[kw_id] = currently_matches

    if is_first_run:
        print("Første kørsel: gemmer baseline, sender ingen mail endnu.")
    elif regressions:
        send_alert_email(regressions)
        print(f"Sendte alarm-mail for {len(regressions)} søgeord.")
    else:
        print("Ingen ændringer at rapportere.")

    save_state(new_state)


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"API-fejl: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        raise
