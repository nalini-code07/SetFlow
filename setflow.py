"""The command-line program: turn songs.json into a timed open-mic setlist,
print it and save it. Options: --tag, --minutes, --name, --show."""
import os
import sys

from helpers import filter_by_tag, load_songs, parse_args, running_order
from models import CurfewError, Setlist, format_mmss
from storage import load_setlists, save_setlist

SONGS_FILE = "songs.json"
DB_FILE = "setlists.db"


def build_setlist(songs, name, minutes):
    """Order the songs and fill a Setlist up to the curfew.

    Returns (setlist, messages) where messages explain every song left out.
    """
    order, held = running_order(songs)
    messages = [f"HELD {song.title}: {song.artist} would play twice in a row"
                for song in held]
    setlist = Setlist(name, minutes * 60)
    for index, song in enumerate(order):
        try:
            setlist.add(song)
        except CurfewError as error:
            messages.append(f"REFUSED {error}")
            not_reached = len(order) - index - 1
            if not_reached > 0:
                messages.append(f"NOT REACHED: {not_reached} more song(s) after the curfew")
            break
    return setlist, messages


def print_setlist(setlist):
    print(f"Setlist: {setlist.name}")
    for position, (start, song) in enumerate(setlist.start_times(), start=1):
        print(f"{position:2d}. {format_mmss(start)}  {song.title} - {song.artist}"
              f" ({format_mmss(song.seconds)})")
    print(setlist.total_line())
    loud = setlist.loud_count()
    print(f"Soundcheck: {setlist.soundcheck_minutes()} min ({loud} loud song(s) x 2 min)")


def show_saved(db_path, name):
    saved = []
    if os.path.exists(db_path):  # do not create an empty database just to read it
        saved = load_setlists(db_path, name)
    if not saved:
        print(f"No saved setlist called '{name}'.")
        return 1
    for item in saved:
        print(f"Setlist #{item['id']}: {item['name']} ({format_mmss(item['total_seconds'])})")
        for entry in item["entries"]:
            print(f"{entry['position']:2d}. {entry['title']} - {entry['artist']}"
                  f" ({format_mmss(entry['seconds'])})")
    return 0


def main(argv, songs_path=SONGS_FILE, db_path=DB_FILE):
    try:
        options = parse_args(argv)
    except ValueError as error:
        print(f"Error: {error}")
        return 1

    if options["show"] is not None:
        return show_saved(db_path, options["show"])

    try:
        songs, skipped = load_songs(songs_path)
    except FileNotFoundError:
        print(f"Error: cannot find {songs_path}")
        return 1
    except ValueError as error:
        print(f"Error: {songs_path} is not usable: {error}")
        return 1
    for line in skipped:
        print(line)
    print(f"Loaded {len(songs)} song(s), skipped {len(skipped)}.")

    tag = options["tag"].lower()
    chosen = filter_by_tag(songs, tag)
    if not chosen:
        print(f"No songs tagged '{tag}'. Nothing saved.")
        return 1
    print(f"Tagged '{tag}': {len(chosen)} song(s).")

    setlist, messages = build_setlist(chosen, options["name"], options["minutes"])
    for line in messages:
        print(line)
    if not setlist.songs:
        print("No song fits before the curfew. Nothing saved.")
        return 1
    print_setlist(setlist)

    setlist_id = save_setlist(db_path, setlist)
    print(f"Saved as setlist #{setlist_id} in {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
