import configparser
import sys
import threading

import keyboard

from device import DeviceSession

key_delete = 'delete'
key_shift = 'shift'
key_end = 'end'
key_home = 'home'


class MusicSession(object):
    # press_callback accepts a list

    is_playing = False

    def __init__(self, music):
        super(MusicSession, self).__init__()
        self.music = music
        self.stored_index = 0
        self.playback_speed = 1.0
        self.process_file()
        self.press_callback = lambda note: print(f"Playing note {note}")
        self.release_callback = lambda note: print(f"Releasing note {note}")
        self.parse_info()

    def set_callback(self, press_callback, release_callback):
        self.press_callback = press_callback
        self.release_callback = release_callback

    def process_file(self) -> (float, int, list):
        with open("song.txt", "r") as macro_file:
            lines = macro_file.read().split("\n")
            time_offset_valid = False
            time_offset = 0
            self.playback_speed = float(lines[0].split("=")[1])
            print("Playback speed is set to %.2f" % self.playback_speed)
            tempo = 60 / float(lines[1].split("=")[1])

            processed_notes = []

            for line in lines[1:]:
                line_split = line.split(" ")
                if len(line_split) < 2:
                    # print("INVALID LINE")
                    continue

                wait_to_press = float(line_split[0])
                notes = line_split[1]
                processed_notes.append([wait_to_press, notes])
                if not time_offset_valid:
                    time_offset = wait_to_press
                    print("Start time offset =", time_offset)
                    time_offset_valid = True
        self.music = [tempo, time_offset, processed_notes]
        return self.music

    def parse_info(self):
        tempo = self.music[0]
        notes = self.music[2][1:]

        # parse time between each note
        # while loop is required because we are editing the array as we go
        i = 0
        while i < len(notes) - 1:
            note = notes[i]
            next_note = notes[i + 1]
            if "tempo" in note[1]:
                tempo = 60 / float(note[1].split("=")[1])
                notes.pop(i)

                note = notes[i]
                if i < len(notes) - 1:
                    next_note = notes[i + 1]
            else:
                note[0] = (next_note[0] - note[0]) * tempo
                i += 1

        # let's just hold the last note for 1 second because we have no data on it
        notes[len(notes) - 1][0] = 1.00
        self.music[2] = notes
        return notes

    def play_next_note(self):
        notes: list = self.music[2]
        if MusicSession.is_playing and self.stored_index < len(self.music[2]):
            note_info = notes[self.stored_index]
            delay = floor_to_zero(note_info[0])
            if note_info[1][0] == "~":
                # release notes
                # parse note_info[1][1:] as int
                self.release_callback(int(note_info[1][1:]))
            else:
                # press notes
                self.press_callback(int(note_info[1]))

            # if "~" not in note_info[1]:
            #     print("%10.2f %15s" % (delay, note_info[1]))
            # print("%10.2f %15s" % (delay/playback_speed,note_info[1]))
            self.stored_index += 1
            if delay == 0:
                self.play_next_note()
            else:
                threading.Timer(delay / self.playback_speed, self.play_next_note).start()
        elif self.stored_index > len(self.music[2]) - 1:
            MusicSession.is_playing = False
            self.stored_index = 0

    def rewind(self, KeyboardEvent):
        if self.stored_index - 10 < 0:
            self.stored_index = 0
        else:
            self.stored_index -= 10
        print("Rewound to %.2f" % self.stored_index)

    def skip(self, KeyboardEvent):
        if self.stored_index + 10 > len(self.music[2]):
            MusicSession.is_playing = False
            stored_index = 0
        else:
            self.stored_index += 10
        print("Skipped to %.2f" % self.stored_index)


class Shared(object):
    current_session: MusicSession = None
    device_session: DeviceSession = None


def on_del_press(event):
    MusicSession.is_playing = not MusicSession.is_playing

    if MusicSession.is_playing:
        print("Playing...")
        Shared.current_session.play_next_note()
    else:
        print("Stopping...")

    return True


def on_home_press(event):
    Shared.current_session.rewind(event)
    return True


def on_end_press(event):
    Shared.current_session.skip(event)
    return True


def floor_to_zero(i):
    if i > 0:
        return i
    else:
        return 0


if __name__ == "__main__":
    # receive command line arguments "--dry-run"
    dry_run = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dry-run":
            print("Dry run mode enabled")
            dry_run = True
    music_sessions = [MusicSession("song.txt")]
    Shared.current_session = music_sessions[0]

    # Read ini file
    config = configparser.ConfigParser()
    config.read('device.ini')
    device_address = config['Device']['Address']

    if not dry_run:
        Shared.device_session = DeviceSession(device_address)
        Shared.current_session.set_callback(Shared.device_session.play_note, Shared.device_session.release_note)

    keyboard.on_press_key(key_delete, on_del_press)
    keyboard.on_press_key(key_home, on_home_press)
    keyboard.on_press_key(key_end, on_end_press)

    print()
    print("Controls")
    print("-" * 20)
    print("Press DELETE to play/pause")
    print("Press HOME to rewind")
    print("Press END to advance")
    while True:
        input("Press Ctrl+C or close window to exit\n\n")
