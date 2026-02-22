"""
SafeClaw Calendar Action - ICS/CalDAV support.

No API keys required - standard protocols.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import dateparser  # type: ignore
from icalendar import Calendar, Event

from safeclaw.actions.base import BaseAction

if TYPE_CHECKING:
    from safeclaw.core.engine import SafeClaw

logger = logging.getLogger(__name__)


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    summary: str
    start: datetime
    end: datetime
    location: str = ""
    description: str = ""
    all_day: bool = False

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def __str__(self) -> str:
        date_fmt = "%Y-%m-%d" if self.all_day else "%Y-%m-%d %H:%M"
        return f"{self.start.strftime(date_fmt)} - {self.summary}"


class CalendarParser:
    """Parses .ics calendar files."""

    def __init__(self) -> None:
        self.events: list[CalendarEvent] = []

    def parse_file(self, path: str | Path) -> bool:
        """Parse an .ics file."""
        try:
            with open(path, 'rb') as f:
                cal = Calendar.from_ical(f.read())

            self.events = []
            for component in cal.walk():
                if component.name == "VEVENT":
                    if isinstance(component, Event):
                        self._parse_event(component)

            # Sort by start date
            self.events.sort(key=lambda x: x.start)
            return True
        except Exception as e:
            logger.error(f"Failed to parse calendar: {e}")
            return False

    def _parse_event(self, component: Event) -> None:
        """Parse a single VEVENT."""
        try:
            summary = str(component.get('summary', 'No Title'))
            location = str(component.get('location', ''))
            description = str(component.get('description', ''))

            dtstart = component.get('dtstart').dt
            dtend = component.get('dtend')

            if dtend:
                dtend = dtend.dt
            else:
                # Default to 1 hour duration if no end time
                if isinstance(dtstart, datetime):
                    dtend = dtstart + timedelta(hours=1)
                else:
                    dtend = dtstart + timedelta(days=1)

            # Handle timezone naive/aware
            # For simplicity in this non-AI tool, we'll keep as-is or ensure UTC?
            # icalendar handles parsing well.

            # Check if all day (date vs datetime)
            all_day = not isinstance(dtstart, datetime)

            # Convert date to datetime for comparison
            if all_day:
                start = datetime.combine(dtstart, datetime.min.time())
                end = datetime.combine(dtend, datetime.min.time())
            else:
                start = dtstart
                end = dtend

            # Ensure timezone awareness consistency if needed
            # For now, we assume naive local time or provided TZ

            self.events.append(CalendarEvent(
                summary=summary,
                start=start,
                end=end,
                location=location,
                description=description,
                all_day=all_day,
            ))
        except Exception as e:
            logger.warning(f"Skipping invalid event: {e}")

    def get_upcoming_events(self, days: int = 7) -> list[CalendarEvent]:
        """Get events for the next N days."""
        now = datetime.now()
        if self.events and self.events[0].start.tzinfo:
             now = datetime.now().astimezone(self.events[0].start.tzinfo)

        limit = now + timedelta(days=days)

        return [
            e for e in self.events
            if e.start >= now and e.start <= limit
        ]

    def get_today_events(self) -> list[CalendarEvent]:
        """Get events for today."""
        return self.get_upcoming_events(days=1)


class CalendarAction(BaseAction):
    """
    Calendar operations.

    Commands:
    - calendar today
    - calendar upcoming
    - calendar import file.ics
    """

    name = "calendar"
    description = "Manage calendar events"

    def __init__(self) -> None:
        self.parser: CalendarParser | None = None

    async def execute(
        self,
        params: dict[str, Any],
        user_id: str,
        channel: str,
        engine: "SafeClaw",
    ) -> str:
        """Execute calendar action."""
        subcommand = params.get("subcommand", "today")

        # Load default calendar if not loaded
        if not self.parser:
            path = await engine.memory.get_preference(user_id, "calendar_path")
            if path:
                self.parser = CalendarParser()
                self.parser.parse_file(path)  # type: ignore

        if subcommand == "import":
            return await self._import_calendar(params, user_id, engine)

        if not self.parser:
            return "No calendar loaded. Use `calendar import --file path/to/cal.ics`"

        if subcommand == "today":
            return self._format_events(self.parser.get_today_events(), "Today's Events")  # type: ignore
        elif subcommand == "upcoming":
            days = int(params.get("days", 7))
            return self._format_events(
                self.parser.get_upcoming_events(days),  # type: ignore
                f"Upcoming Events ({days} days)"
            )
        else:
            return f"Unknown subcommand: {subcommand}"

    async def _import_calendar(
        self,
        params: dict[str, Any],
        user_id: str,
        engine: "SafeClaw"
    ) -> str:
        """Import an ICS file."""
        path_str = params.get("file") or params.get("path")
        if not path_str:
            return "Please specify a file path: `calendar import --file my.ics`"

        path = Path(path_str).expanduser()
        if not path.exists():
            return f"File not found: {path}"

        self.parser = CalendarParser()
        if self.parser.parse_file(path):
            # Save preference
            await engine.memory.set_preference(user_id, "calendar_path", str(path))
            return f"✅ Loaded calendar with {len(self.parser.events)} events"
        else:
            return "❌ Failed to parse calendar file"

    def _format_events(self, events: list[CalendarEvent], title: str) -> str:
        """Format events list."""
        if not events:
            return f"{title}: No events found."

        lines = [f"📅 **{title}**", ""]
        for e in events:
            time_str = "All Day" if e.all_day else e.start.strftime("%H:%M")
            lines.append(f"• **{time_str}** {e.summary}")
            if e.location:
                lines.append(f"  📍 {e.location}")

        return "\n".join(lines)
