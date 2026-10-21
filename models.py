"""The two classes SetFlow is built on: Song and Setlist."""


class SongError(ValueError):
    """A record in the catalogue cannot become a Song."""


class CurfewError(Exception):
    """Adding a song would push the setlist past the curfew."""


def format_mmss(total_seconds):
    """Turn 1450 into '24:10'. Minutes are not capped at 59."""
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


class Song:
    def __init__(self, song_id, title, artist, seconds, tags):
        self.song_id = song_id
        self.title = title
        self.artist = artist
        self.seconds = seconds
        self.tags = tags

    def has_tag(self, tag):
        return tag.lower() in self.tags

    def is_loud(self):
        return self.has_tag("loud")

    def __repr__(self):
        return f"Song({self.song_id}, {self.title!r}, {self.artist!r}, {self.seconds})"


class Setlist:
    LOUD_SOUNDCHECK_MINUTES = 2

    def __init__(self, name, curfew_seconds):
        self.name = name
        self.curfew_seconds = curfew_seconds
        self.songs = []

    def total_seconds(self):
        return sum([song.seconds for song in self.songs])

    def add(self, song):
        """Append a song, or raise CurfewError and leave the setlist unchanged."""
        finish = self.total_seconds() + song.seconds
        if finish > self.curfew_seconds:
            raise CurfewError(
                f"{song.title}: would end at {format_mmss(finish)}, "
                f"curfew {format_mmss(self.curfew_seconds)}"
            )
        self.songs.append(song)

    def start_times(self):
        """A list of (start_seconds, song) pairs, the first starting at 0."""
        rows = []
        clock = 0
        for song in self.songs:
            rows.append((clock, song))
            clock = clock + song.seconds
        return rows

    def loud_count(self):
        return len([song for song in self.songs if song.is_loud()])

    def soundcheck_minutes(self):
        return self.loud_count() * self.LOUD_SOUNDCHECK_MINUTES

    def total_line(self):
        return f"Total: {format_mmss(self.total_seconds())} / {format_mmss(self.curfew_seconds)}"
