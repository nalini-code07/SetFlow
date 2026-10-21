import contextlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import unittest

from models import Setlist, Song
from setflow import main
from storage import load_setlists, save_setlist


def make_setlist(name):
    setlist = Setlist(name, 25 * 60)
    setlist.add(Song(5, "Copper Kettle", "Old Pine Trio", 158, ["acoustic"]))
    setlist.add(Song(9, "Slow Thaw", "June Avery", 333, ["acoustic"]))
    return setlist


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.db_path = os.path.join(self.folder, "setlists.db")

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_saved_rows(self):
        setlist_id = save_setlist(self.db_path, make_setlist("Friday"))
        conn = sqlite3.connect(self.db_path)
        try:
            head = conn.execute("SELECT name, total_seconds FROM setlist WHERE id = ?",
                                (setlist_id,)).fetchall()
            rows = conn.execute(
                "SELECT setlist_id, position, title, artist, seconds FROM entry "
                "ORDER BY position").fetchall()
        finally:
            conn.close()
        self.assertEqual(head, [("Friday", 491)])
        self.assertEqual(rows, [
            (setlist_id, 1, "Copper Kettle", "Old Pine Trio", 158),
            (setlist_id, 2, "Slow Thaw", "June Avery", 333),
        ])

    def test_same_name_twice_keeps_both(self):
        first = save_setlist(self.db_path, make_setlist("Friday"))
        second_list = make_setlist("Friday")
        second_list.songs.pop()
        second = save_setlist(self.db_path, second_list)
        save_setlist(self.db_path, make_setlist("Saturday"))
        saved = load_setlists(self.db_path, "Friday")
        self.assertEqual([item["id"] for item in saved], [first, second])
        self.assertEqual(len(saved[0]["entries"]), 2)
        self.assertEqual(len(saved[1]["entries"]), 1)
        self.assertEqual(saved[1]["total_seconds"], 158)

    def test_unknown_name_gives_empty_list(self):
        save_setlist(self.db_path, make_setlist("Friday"))
        self.assertEqual(load_setlists(self.db_path, "Sunday"), [])


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.db_path = os.path.join(self.folder, "setlists.db")
        self.songs_path = os.path.join(self.folder, "songs.json")
        records = [
            {"id": 1, "title": "One", "artist": "A", "seconds": 600, "tags": ["acoustic"]},
            {"id": 2, "title": "Two", "artist": "B", "seconds": 700, "tags": ["acoustic", "loud"]},
            {"id": 3, "title": "Three", "artist": "C", "seconds": 300, "tags": ["acoustic"]},
            {"id": 7, "title": "Bad", "artist": "D", "seconds": "x", "tags": ["acoustic"]},
        ]
        with open(self.songs_path, "w", encoding="utf-8") as handle:
            json.dump(records, handle)

    def tearDown(self):
        shutil.rmtree(self.folder)

    def run_main(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(argv, songs_path=self.songs_path, db_path=self.db_path)
        return code, buffer.getvalue().splitlines()

    def test_bad_minutes_prints_error_and_writes_nothing(self):
        for bad in ["abc", "0", "-3", "12.5"]:
            code, lines = self.run_main(["--tag", "acoustic", "--minutes", bad])
            self.assertEqual(code, 1)
            self.assertEqual(lines, ["Error: bad minutes"])
        self.assertFalse(os.path.exists(self.db_path))

    def test_full_run_prints_and_saves(self):
        code, lines = self.run_main(["--tag", "acoustic", "--minutes", "25",
                                     "--name", "Test Night"])
        self.assertEqual(code, 0)
        self.assertEqual(lines[0], "SKIPPED 7: bad seconds")
        self.assertIn("REFUSED One: would end at 26:40, curfew 25:00", lines)
        self.assertIn("Total: 16:40 / 25:00", lines)
        self.assertIn("Soundcheck: 2 min (1 loud song(s) x 2 min)", lines)
        saved = load_setlists(self.db_path, "Test Night")
        self.assertEqual(len(saved), 1)
        self.assertEqual([e["title"] for e in saved[0]["entries"]], ["Three", "Two"])

    def test_show_lists_every_setlist_with_the_name(self):
        self.run_main(["--tag", "acoustic", "--name", "Twice"])
        self.run_main(["--tag", "acoustic", "--name", "Twice"])
        code, lines = self.run_main(["--show", "Twice"])
        self.assertEqual(code, 0)
        headers = [line for line in lines if line.startswith("Setlist #")]
        self.assertEqual(headers, ["Setlist #1: Twice (16:40)", "Setlist #2: Twice (16:40)"])

    def test_show_before_any_save_creates_no_database(self):
        code, lines = self.run_main(["--show", "Friday"])
        self.assertEqual(code, 1)
        self.assertEqual(lines, ["No saved setlist called 'Friday'."])
        self.assertFalse(os.path.exists(self.db_path))

    def test_unknown_tag_saves_nothing(self):
        code, lines = self.run_main(["--tag", "jazz"])
        self.assertEqual(code, 1)
        self.assertEqual(lines[-1], "No songs tagged 'jazz'. Nothing saved.")
        self.assertFalse(os.path.exists(self.db_path))


if __name__ == "__main__":
    unittest.main()
