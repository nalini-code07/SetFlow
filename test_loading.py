import json
import os
import shutil
import tempfile
import unittest

from helpers import load_songs, parse_args, parse_minutes, song_from_record
from models import SongError


def good_record(**changes):
    record = {"id": 1, "title": "Paper Boats", "artist": "The Tidewaters",
              "seconds": 187, "tags": ["acoustic"]}
    record.update(changes)
    return record


class SongFromRecordTests(unittest.TestCase):
    def test_good_record_becomes_song(self):
        song = song_from_record(good_record(tags=["Acoustic", " LOUD "]))
        self.assertEqual(song.title, "Paper Boats")
        self.assertEqual(song.seconds, 187)
        self.assertEqual(song.tags, ["acoustic", "loud"])

    def test_numeric_string_seconds_is_accepted(self):
        self.assertEqual(song_from_record(good_record(seconds="201")).seconds, 201)

    def test_reasons(self):
        cases = [
            (good_record(seconds="four minutes"), "bad seconds"),
            (good_record(seconds=None), "bad seconds"),
            (good_record(seconds=True), "bad seconds"),
            (good_record(seconds=0), "bad seconds"),
            (good_record(seconds=-30), "bad seconds"),
            (good_record(title=""), "missing title"),
            (good_record(title="   "), "missing title"),
            (good_record(artist=42), "missing artist"),
            (good_record(tags="acoustic"), "bad tags"),
            (["not", "a", "dict"], "not a record"),
        ]
        for record, reason in cases:
            with self.assertRaises(SongError) as caught:
                song_from_record(record)
            self.assertEqual(str(caught.exception), reason)

    def test_missing_title_key(self):
        record = good_record()
        del record["title"]
        with self.assertRaises(SongError) as caught:
            song_from_record(record)
        self.assertEqual(str(caught.exception), "missing title")


class LoadSongsTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "songs.json")

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write(self, records):
        with open(self.path, "w", encoding="utf-8", newline="\r\n") as handle:
            json.dump(records, handle, indent=2)

    def test_skipper_reports_each_bad_record_on_one_line(self):
        self.write([
            good_record(id=1),
            good_record(id=7, seconds="four minutes"),
            good_record(id=8, title=None),
            good_record(id=1, title="Copy"),
            good_record(id=9, title="Window Seat"),
        ])
        songs, skipped = load_songs(self.path)
        self.assertEqual([song.song_id for song in songs], [1, 9])
        self.assertEqual(skipped, [
            "SKIPPED 7: bad seconds",
            "SKIPPED 8: missing title",
            "SKIPPED 1: duplicate id",
        ])

    def test_record_without_id_shows_question_mark(self):
        record = good_record()
        del record["id"]
        self.write([record])
        songs, skipped = load_songs(self.path)
        self.assertEqual(songs, [])
        self.assertEqual(skipped, ["SKIPPED ?: missing id"])

    def test_broken_json_raises_value_error(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write('[{"id": 1,')
        with self.assertRaises(ValueError):
            load_songs(self.path)

    def test_top_level_must_be_a_list(self):
        self.write({"id": 1})
        with self.assertRaises(ValueError):
            load_songs(self.path)


class ArgumentTests(unittest.TestCase):
    def test_parse_minutes(self):
        self.assertEqual(parse_minutes("25"), 25)
        for bad in ["abc", "", "25.5", "0", "-5", "601"]:
            with self.assertRaises(ValueError) as caught:
                parse_minutes(bad)
            self.assertEqual(str(caught.exception), "bad minutes")

    def test_parse_args_defaults(self):
        options = parse_args(["--tag", "acoustic"])
        self.assertEqual(options["tag"], "acoustic")
        self.assertEqual(options["minutes"], 25)
        self.assertEqual(options["name"], "Open Mic")

    def test_minutes_without_value_is_bad_minutes(self):
        with self.assertRaises(ValueError) as caught:
            parse_args(["--tag", "acoustic", "--minutes"])
        self.assertEqual(str(caught.exception), "bad minutes")

    def test_tag_is_required(self):
        with self.assertRaises(ValueError) as caught:
            parse_args(["--minutes", "25"])
        self.assertEqual(str(caught.exception), "--tag is required")

    def test_unknown_option(self):
        with self.assertRaises(ValueError):
            parse_args(["--tag", "acoustic", "--colour", "red"])


if __name__ == "__main__":
    unittest.main()
