"""Parse raw_epg.xml (XMLTV) into channel and programme records."""
from datetime import datetime

from lxml import etree

INPUT_PATH = "raw_epg.xml"
TIME_FORMAT = "%Y%m%d%H%M%S %z"


def _text(element, tag):
    """Return the stripped text of a child tag, or None if it's missing/empty."""
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_time(raw_value):
    """Parse an XMLTV timestamp like '20260701200000 +0100' into a datetime."""
    if not raw_value:
        return None
    try:
        return datetime.strptime(raw_value, TIME_FORMAT)
    except ValueError:
        return None


def parse_channels(root):
    channels = []
    for channel_el in root.findall("channel"):
        channels.append({
            "channel_id": channel_el.get("id"),
            "display_name": _text(channel_el, "display-name"),
        })
    return channels


def parse_programmes(root):
    programmes = []
    for programme_el in root.findall("programme"):
        start = _parse_time(programme_el.get("start"))
        stop = _parse_time(programme_el.get("stop"))

        duration_minutes = None
        if start is not None and stop is not None:
            duration_minutes = round((stop - start).total_seconds() / 60)

        programmes.append({
            "channel_id": programme_el.get("channel"),
            "start": start,
            "stop": stop,
            "duration_minutes": duration_minutes,
            "title": _text(programme_el, "title"),
            "description": _text(programme_el, "desc"),
            "category": _text(programme_el, "category"),
        })
    return programmes


def parse_epg(path=INPUT_PATH):
    """Parse an XMLTV file and return (channels, programmes) as lists of dicts."""
    tree = etree.parse(path)
    root = tree.getroot()
    channels = parse_channels(root)
    programmes = parse_programmes(root)
    return channels, programmes


def print_sample(programmes, count=5):
    print(f"\n--- Sample of {count} parsed programmes ---\n")
    for p in programmes[:count]:
        print(f"[{p['channel_id']}] {p['title']}  ({p['duration_minutes']} min)")
        print(f"  {p['start']} -> {p['stop']}")
        print(f"  category: {p['category']}")
        print(f"  description: {p['description']}")
        print()


def main():
    channels, programmes = parse_epg()
    print(f"Parsed {len(channels)} channels and {len(programmes)} programmes")
    print_sample(programmes)


if __name__ == "__main__":
    main()