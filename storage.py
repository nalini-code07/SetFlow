"""Saving and loading setlists in an sqlite3 database file."""
import sqlite3

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS setlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        total_seconds INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS entry (
        setlist_id INTEGER NOT NULL REFERENCES setlist(id),
        position INTEGER NOT NULL,
        title TEXT NOT NULL,
        artist TEXT NOT NULL,
        seconds INTEGER NOT NULL
    )""",
]


def connect(db_path):
    conn = sqlite3.connect(db_path)
    for statement in SCHEMA:
        conn.execute(statement)
    return conn


def save_setlist(db_path, setlist):
    """Insert the setlist and its entries in one transaction. Returns the new id."""
    conn = connect(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO setlist (name, total_seconds) VALUES (?, ?)",
                (setlist.name, setlist.total_seconds()),
            )
            setlist_id = cursor.lastrowid
            rows = [(setlist_id, position, song.title, song.artist, song.seconds)
                    for position, song in enumerate(setlist.songs, start=1)]
            conn.executemany(
                "INSERT INTO entry (setlist_id, position, title, artist, seconds) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
    finally:
        conn.close()
    return setlist_id


def load_setlists(db_path, name):
    """Every saved setlist with this name, oldest first, each as a dictionary."""
    conn = connect(db_path)
    try:
        heads = conn.execute(
            "SELECT id, name, total_seconds FROM setlist WHERE name = ? ORDER BY id",
            (name,),
        ).fetchall()
        result = []
        for setlist_id, saved_name, total in heads:
            entries = conn.execute(
                "SELECT position, title, artist, seconds FROM entry "
                "WHERE setlist_id = ? ORDER BY position",
                (setlist_id,),
            ).fetchall()
            result.append({
                "id": setlist_id,
                "name": saved_name,
                "total_seconds": total,
                "entries": [{"position": p, "title": t, "artist": a, "seconds": s}
                            for p, t, a, s in entries],
            })
    finally:
        conn.close()
    return result
