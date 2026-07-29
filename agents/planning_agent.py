from agents.base_agent import BaseAgent
from agents.google_auth import get_google_credentials
from utils.google_oauth import get_credentials_for_user
from googleapiclient.discovery import build
from datetime import datetime, timedelta, time
import json
from utils.settings import is_debug_enabled

class PlanningAgent(BaseAgent):
    """
    AI agent responsible for analyzing calendar events
    and generating planning recommendations.
    """
    model_name = "qwen2.5:7b"
    temperature = 0.2
    max_tokens = 400
    system_prompt = """You are the Orbit Planning & Priority Agent.

You receive a JSON list of calendar events (today and tomorrow) with an assigned priority
(1=funding/investors, 2=customers/prospects, 3=internal) and a list of detected time conflicts.

Your job: write a short professional daily briefing in English, no more than 6 lines, that:
1. Summarizes today's and tomorrow's schedule
2. Highlights any detected conflicts clearly
3. States what to focus on first based on priority

IMPORTANT: The priority number (1/2/3) is a rough sorting label, not a guaranteed description
of the event's nature. Look at the actual event title before describing what kind of event it
is. Do NOT call an event a "customer meeting" or "investor meeting" just because of its priority
number — describe it using its actual title. If a title is ambiguous or looks personal/administrative
(e.g. remote work, time off, a personal appointment), describe it neutrally instead of guessing
it's a business meeting.

Do NOT invent events that are not in the data. Do NOT add markdown headers or emojis.
Answer in plain text only.
"""

    PRIORITY_KEYWORDS = {
        1: ["investor", "investisseur", "funding", "fundraising", "levée de fonds", "vc ", "term sheet"],
        2: ["client", "prospect", "customer", "quotation", "devis", "site visit", "demo"],
        3: [
            "internal", "interne", "équipe", "team meeting", "1:1", "sync", "standup",
            # Événements personnels / administratifs / culturels — non liés à
            # une activité commerciale, donc classés "interne" par défaut
            # plutôt que faussement étiquetés "client".
            "télétravail", "teletravail", "teltravail", "remote", "wfh",
            "congé", "conge", "vacances", "absence", "off",
            "ftour", "iftar", "ramadan", "prière", "priere",
            "rdv perso", "personnel", "médecin", "medecin", "dentiste",
        ],
    }


    def get_calendar_service(self, email: str = None):
        """Legacy path: local single-user desktop OAuth flow. Unchanged."""
        creds = get_google_credentials(email=email)
        return build("calendar", "v3", credentials=creds)

    def get_calendar_service_for_user(self, user_id: int):
        """New path: per-user web OAuth flow, credentials from PostgreSQL."""
        creds = get_credentials_for_user(user_id)
        return build("calendar", "v3", credentials=creds)

    def _build_briefing(self, service) -> dict:
        """Shared logic between run() and run_for_user() — avoids duplicating
        the whole event-fetching/prioritizing/briefing pipeline twice."""
        today_events, tomorrow_events = self.get_today_and_tomorrow_events(service)
        today_events = self.prioritize_events(today_events)
        tomorrow_events = self.prioritize_events(tomorrow_events)
        all_events = today_events + tomorrow_events
        conflicts = self.detect_conflicts(all_events)
        payload = {"today": today_events, "tomorrow": tomorrow_events, "conflicts": conflicts}
        briefing = self.call_llm(json.dumps(payload, ensure_ascii=False))
        return {
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "conflicts": conflicts,
            "briefing": briefing,
        }

    def get_events_for_range(self, service, start_dt, end_dt, calendar_id="primary"):
        time_min = start_dt.isoformat()
        time_max = end_dt.isoformat()
        if is_debug_enabled():
            print(f"[DEBUG] Calendar query: {time_min} → {time_max}")
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        raw_events = events_result.get("items", [])
        events = []

        for ev in raw_events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            end = ev["end"].get("dateTime", ev["end"].get("date"))
            events.append({
                "id": ev.get("id"),
                "title": ev.get("summary", "(sans titre)"),
                "start": start,
                "end": end,
                "location": ev.get("location", ""),
                "attendees": [a.get("email") for a in ev.get("attendees", [])],
                "description": ev.get("description", ""),
            })

        return events

    def get_today_and_tomorrow_events(self, service):
        now = datetime.now().astimezone()
        local_tz = now.tzinfo

        today_start = datetime.combine(now.date(), time.min).replace(tzinfo=local_tz)
        today_end   = datetime.combine(now.date(), time.max).replace(tzinfo=local_tz)
        tomorrow_start = datetime.combine(
            (now + timedelta(days=1)).date(), time.min
        ).replace(tzinfo=local_tz)
        tomorrow_end = datetime.combine(
            (now + timedelta(days=1)).date(), time.max
        ).replace(tzinfo=local_tz)

        today_events    = self.get_events_for_range(service, today_start, today_end)
        tomorrow_events = self.get_events_for_range(service, tomorrow_start, tomorrow_end)

        return today_events, tomorrow_events

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            dt = datetime.fromisoformat(value + "T00:00:00")

        # Normalise : si l'événement n'a pas de fuseau horaire (cas des
        # événements "toute la journée", ex: "2026-07-12"), on lui assigne le
        # fuseau local pour pouvoir le comparer sans erreur aux événements
        # horodatés qui, eux, sont toujours timezone-aware côté Google Calendar.
        if dt.tzinfo is None:
            dt = dt.astimezone()

        return dt

    def detect_conflicts(self, events: list) -> list:
        conflicts = []
        parsed = [(ev, self._parse_dt(ev["start"]), self._parse_dt(ev["end"])) for ev in events]

        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                ev_a, start_a, end_a = parsed[i]
                ev_b, start_b, end_b = parsed[j]

                if start_a < end_b and start_b < end_a:
                    conflicts.append({
                        "event_a": ev_a["title"],
                        "event_b": ev_b["title"],
                        "time_a": ev_a["start"],
                        "time_b": ev_b["start"],
                    })

        return conflicts

    def assign_priority(self, event: dict) -> int:
        text = f"{event['title']} {event.get('description', '')}".lower()

        for priority in (1, 2, 3):
            if any(keyword in text for keyword in self.PRIORITY_KEYWORDS[priority]):
                return priority

        # Défaut changé de 2 à 3 : un événement sans mot-clé reconnu est
        # traité comme "interne/à vérifier" plutôt que présumé "client" —
        # évite qu'un événement personnel (ex: "ftour", "télétravail")
        # soit faussement décrit comme un rendez-vous commercial dans le
        # briefing généré par le LLM.
        return 3

    def prioritize_events(self, events: list) -> list:
        for ev in events:
            ev["priority"] = self.assign_priority(ev)
        return sorted(events, key=lambda e: (e["priority"], e["start"]))

    def run(self, email: str = None):
        """Legacy entry point — unchanged, still used for CLI/dev testing."""
        service = self.get_calendar_service(email=email)
        return self._build_briefing(service)

    def run_for_user(self, user_id: int):
        """New entry point for the API: builds this user's own briefing,
        using their own connected Google Calendar."""
        service = self.get_calendar_service_for_user(user_id)
        return self._build_briefing(service)
if __name__ == "__main__":
    agent = PlanningAgent()
    result = agent.run()

    print(f"Today: {len(result['today_events'])} event(s)")
    print(f"Tomorrow: {len(result['tomorrow_events'])} event(s)")
    print(f"Conflicts detected: {len(result['conflicts'])}\n")

    if result["conflicts"]:
        print("CONFLICTS:")
        for c in result["conflicts"]:
            print(f"  - '{c['event_a']}' ({c['time_a']}) overlaps with '{c['event_b']}' ({c['time_b']})")
        print()

    print("=" * 50)
    print("DAILY BRIEFING")
    print("=" * 50)
    print(result["briefing"])
     
    """ Google Authentication
                │
                ▼
        Connect to Google Calendar
                │
                ▼
        Retrieve upcoming events
                │
                ▼
        Detect conflicts and priorities
                │
                ▼
        Build a JSON payload
                │
                ▼
        Send the payload to Qwen (via Ollama)
                │
                ▼
        Generate a planning briefing
                │
                ▼
        Return the planning summary """