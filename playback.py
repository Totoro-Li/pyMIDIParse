import argparse
import configparser
import os
import threading
import time

import keyboard

from driver.device import DeviceSession
from midi.midi_trans import get_file_choice, get_midi_file_name, process_midi

key_p = 'p'
key_r = 'r'
key_a = 'a'
key_z = 'z'


class MusicSession(object):
    is_playing = True
    songs_folder = "songs"
    scripts_folder = "scripts"
    current_session = None
    device_session: DeviceSession = None

    def __init__(self, script_file):
        super(MusicSession, self).__init__()
        self.music = None
        self.script_file = script_file
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
        with open(os.path.join(self.scripts_folder, self.script_file), 'r') as f:
            lines = f.read().split("\n")
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

    def rewind(self):
        if self.stored_index - 10 < 0:
            self.stored_index = 0
        else:
            self.stored_index -= 10
        print("Rewound to %.2f" % self.stored_index)

    def skip(self):
        if self.stored_index + 10 > len(self.music[2]):
            MusicSession.is_playing = False
            stored_index = 0
        else:
            self.stored_index += 10
        print("Skipped to %.2f" % self.stored_index)


def on_key_p_press(event):
    MusicSession.is_playing = not MusicSession.is_playing

    if MusicSession.is_playing and MusicSession.current_session is not None:
        print("Playing...")
        MusicSession.current_session.play_next_note()
    elif MusicSession.current_session is None:
        print("No song selected")
    else:
        print("Stopping...")

    return True


def on_key_r_press(event):
    MusicSession.current_session.rewind()
    return True


def on_key_a_press(event):
    MusicSession.current_session.skip()
    return True


def on_key_z_press(event):
    on_key_p_press(event)
    target = get_file_choice(MusicSession.songs_folder)
    # if target file exists in scripts folder, use that
    if not os.path.exists(os.path.join(MusicSession.scripts_folder, get_midi_file_name(target) + ".txt")):
        process_midi(os.path.join(MusicSession.songs_folder, target))
    MusicSession.current_session = MusicSession(get_midi_file_name(target) + ".txt")

def floor_to_zero(i):
    return i if i > 0 else 0


def print_help():
    print()
    print("Controls")
    print("-" * 20)
    print("Press P to play/pause")
    print("Press R to rewind")
    print("Press A to advance")
    print("Press Z to select a song")


if __name__ == "__main__":
    # Option parser from command line
    parser = argparse.ArgumentParser(description='Song playback options')
    parser.add_argument('--dry-run', action='store_true', help='Run without sending commands to the device')
    parser.add_argument('-f', '--songs-folder', type=str, help="Path to the folder containing the songs, defaults to './songs'")

    args = parser.parse_args()
    dry_run = args.dry_run
    songs_folder = args.songs_folder

    if songs_folder is not None:
        MusicSession.songs_folder = songs_folder

    # Read ini file
    config = configparser.ConfigParser()
    config.read('driver/device.ini')
    device_address = config['Device']['Address']

    if not dry_run:
        MusicSession.device_session = DeviceSession(device_address)
        MusicSession.current_session.set_callback(MusicSession.device_session.play_note, MusicSession.device_session.release_note)

    keyboard.on_press_key(key_p, on_key_p_press)
    keyboard.on_press_key(key_r, on_key_r_press)
    keyboard.on_press_key(key_a, on_key_a_press)
    keyboard.on_press_key(key_z, on_key_z_press)

    print_help()
    on_key_z_press(None)
    on_key_p_press(None)

    time.sleep(100000)
