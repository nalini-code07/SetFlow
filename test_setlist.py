import unittest

from helpers import filter_by_tag, running_order
from models import CurfewError, Setlist, Song, format_mmss
from setflow import build_setlist


def song(song_id, artist, seconds, tags=None):
    return Song(song_id, f"Song {song_id}", artist, seconds, tags or ["acoustic"])


class FormatTests(unittest.TestCase):
    def test_format_mmss(self):
        self.assertEqual(format_mmss(0), "00:00")
        self.assertEqual(format_mmss(1450), "24:10")
        self.assertEqual(format_mmss(1500), "25:00")
        self.assertEqual(format_mmss(6005), "100:05")


class CurfewTests(unittest.TestCase):
    def test_song_that_fits_exactly_is_kept(self):
        setlist = Setlist("Exact", 10 * 60)
        setlist.add(song(1, "A", 300))
        setlist.add(song(2, "B", 300))
        self.assertEqual(setlist.total_seconds(), 600)
        self.assertEqual(setlist.total_line(), "Total: 10:00 / 10:00")

    def test_song_that_breaks_curfew_is_refused(self):
        setlist = Setlist("Tight", 25 * 60)
        setlist.add(song(1, "A", 1400))
        with self.assertRaises(CurfewError) as caught:
            setlist.add(song(2, "B", 101))
        self.assertIn("would end at 25:01", str(caught.exception))
        self.assertEqual(len(setlist.songs), 1)
        self.assertEqual(setlist.total_line(), "Total: 23:20 / 25:00")

    def test_build_stops_at_first_refusal(self):
        songs = [song(1, "A", 100), song(2, "B", 600), song(3, "C", 200),
                 song(4, "D", 500)]
        setlist, messages = build_setlist(songs, "Night", 15)
        # Order is 1 (short), 2 (long), 3 (short), 4 (long); 4 ends at 23:20.
        self.assertEqual([s.song_id for s in setlist.songs], [1, 2, 3])
        self.assertEqual(setlist.total_seconds(), 900)
        self.assertEqual(messages, ["REFUSED Song 4: would end at 23:20, curfew 15:00"])
        self.assertLessEqual(setlist.total_seconds(), 15 * 60)

    def test_songs_after_refusal_are_reported(self):
        songs = [song(1, "A", 60), song(2, "B", 900), song(3, "C", 70),
                 song(4, "D", 800)]
        setlist, messages = build_setlist(songs, "Night", 10)
        self.assertEqual([s.song_id for s in setlist.songs], [1])
        self.assertEqual(messages[1], "NOT REACHED: 2 more song(s) after the curfew")

    def test_start_times(self):
        setlist = Setlist("Times", 30 * 60)
        for item in [song(1, "A", 158), song(2, "B", 333), song(3, "C", 187)]:
            setlist.add(item)
        starts = [format_mmss(start) for start, item in setlist.start_times()]
        self.assertEqual(starts, ["00:00", "02:38", "08:11"])


class OrderTests(unittest.TestCase):
    def test_short_opener_then_alternates(self):
        songs = [song(1, "A", 300), song(2, "B", 100), song(3, "C", 500),
                 song(4, "D", 200)]
        order, held = running_order(songs)
        self.assertEqual([s.seconds for s in order], [100, 500, 200, 300])
        self.assertEqual(held, [])

    def test_no_artist_twice_in_a_row(self):
        songs = [song(1, "Mira", 100), song(2, "mira", 110), song(3, "Kofi", 400),
                 song(4, "Mira", 120), song(5, "Kofi", 130), song(6, "June", 500)]
        order, held = running_order(songs)
        for before, after in zip(order, order[1:]):
            self.assertNotEqual(before.artist.lower(), after.artist.lower())
        self.assertEqual(len(order) + len(held), 6)

    def test_same_artist_left_over_is_held(self):
        songs = [song(1, "Solo", 100), song(2, "Solo", 200), song(3, "Other", 300)]
        order, held = running_order(songs)
        self.assertEqual([s.song_id for s in order], [1, 3, 2])
        self.assertEqual(held, [])
        order, held = running_order(songs + [song(4, "Solo", 400)])
        self.assertEqual([s.song_id for s in held], [4])


class TagAndSoundcheckTests(unittest.TestCase):
    def test_filter_by_tag_ignores_case(self):
        songs = [song(1, "A", 100, ["acoustic"]), song(2, "B", 100, ["loud"])]
        self.assertEqual([s.song_id for s in filter_by_tag(songs, "ACOUSTIC")], [1])

    def test_each_loud_song_adds_two_minutes(self):
        setlist = Setlist("Loud", 60 * 60)
        setlist.add(song(1, "A", 100, ["loud", "acoustic"]))
        setlist.add(song(2, "B", 100, ["acoustic"]))
        setlist.add(song(3, "C", 100, ["loud"]))
        self.assertEqual(setlist.loud_count(), 2)
        self.assertEqual(setlist.soundcheck_minutes(), 4)


if __name__ == "__main__":
    unittest.main()
