"""Helper functions: command-line parsing, loading songs.json, ordering."""
import json

from models import Song, SongError

DEFAULTS = {"tag": None, "minutes": "25", "name": "Open Mic", "show": None}


def parse_args(argv):
    """Turn ['--tag', 'acoustic', '--minutes', '25'] into a dictionary.

    Raises ValueError with the message to print when something is wrong.
    """
    options = dict(DEFAULTS)
    i = 0
    while i < len(argv):
        flag = argv[i]
        key = flag[2:]
        if not flag.startswith("--") or key not in options:
            raise ValueError(f"unknown option {flag}")
        if i + 1 >= len(argv):
            if key == "minutes":
                raise ValueError("bad minutes")
            raise ValueError(f"{flag} needs a value")
        options[key] = argv[i + 1]
        i = i + 2
    options["minutes"] = parse_minutes(options["minutes"])
    if options["show"] is None and not options["tag"]:
        raise ValueError("--tag is required")
    return options


def parse_minutes(text):
    """'25' -> 25. Anything that is not a whole number from 1 to 600 is bad."""
    try:
        minutes = int(text)
    except ValueError:
        raise ValueError("bad minutes")
    if minutes < 1 or minutes > 600:
        raise ValueError("bad minutes")
    return minutes


def song_from_record(record):
    """Build a Song from one JSON record, or raise SongError with the reason."""
    if not isinstance(record, dict):
        raise SongError("not a record")
    if "id" not in record:
        raise SongError("missing id")
    for key in ["title", "artist"]:
        value = record.get(key)
        if not isinstance(value, str) or value.strip() == "":
            raise SongError(f"missing {key}")
    raw_seconds = record.get("seconds")
    if isinstance(raw_seconds, bool):
        raise SongError("bad seconds")
    try:
        seconds = int(raw_seconds)
    except (ValueError, TypeError):
        raise SongError("bad seconds")
    if seconds <= 0:
        raise SongError("bad seconds")
    tags = record.get("tags", [])
    if not isinstance(tags, list):
        raise SongError("bad tags")
    clean_tags = [str(tag).strip().lower() for tag in tags]
    return Song(record["id"], record["title"].strip(), record["artist"].strip(),
                seconds, clean_tags)


def load_songs(path):
    """Return (songs, skip_lines). Raises OSError or ValueError for a bad file."""
    with open(path, "r", encoding="utf-8") as handle:
        records = json.load(handle)
    if not isinstance(records, list):
        raise ValueError("songs file must hold a JSON list")
    songs = []
    skipped = []
    seen_ids = set()
    for record in records:
        song_id = "?"
        if isinstance(record, dict):
            song_id = record.get("id", "?")
        try:
            song = song_from_record(record)
            if song.song_id in seen_ids:
                raise SongError("duplicate id")
        except SongError as error:
            skipped.append(f"SKIPPED {song_id}: {error}")
            continue
        seen_ids.add(song.song_id)
        songs.append(song)
    return songs, skipped


def filter_by_tag(songs, tag):
    return [song for song in songs if song.has_tag(tag)]


def by_length(song):
    """Sort key: shortest first, title breaks ties so the order is repeatable."""
    return (song.seconds, song.title.lower())


def running_order(songs):
    """Order songs: short opener, then long/short alternating, never the same
    artist twice in a row. Returns (order, held_back)."""
    remaining = sorted(songs, key=by_length)
    order = []
    want_short = True
    while remaining:
        if want_short:
            candidates = remaining
        else:
            candidates = list(reversed(remaining))
        pick = None
        for song in candidates:
            if not order or song.artist.lower() != order[-1].artist.lower():
                pick = song
                break
        if pick is None:
            # Everything left is by the artist who just played.
            return order, remaining
        order.append(pick)
        remaining.remove(pick)
        want_short = not want_short
    return order, []
