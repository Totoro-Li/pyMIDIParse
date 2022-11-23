import os


class MidiFile:
    startSequence = [[0x4D, 0x54, 0x68, 0x64],  # MThd
                     [0x4D, 0x54, 0x72, 0x6B],  # MTrk
                     [0xFF]  # FF
                     ]

    typeDict = {0x00: "Sequence Number",
                0x01: "Text Event",
                0x02: "Copyright Notice",
                0x03: "Sequence/Track Name",
                0x04: "Instrument Name",
                0x05: "Lyric",
                0x06: "Marker",
                0x07: "Cue Point",
                0x20: "MIDI Channel Prefix",
                0x2F: "End of Track",
                0x51: "Set Tempo",
                0x54: "SMTPE Offset",
                0x58: "Time Signature",
                0x59: "Key Signature",
                0x7F: "Sequencer-Specific Meta-event",
                0x21: "Prefix Port",
                0x09: "Other text format [0x09]",
                0x08: "Other text format [0x08]",
                0x0A: "Other text format [0x0A]",
                0x0C: "Other text format [0x0C]"
                }

    def __init__(self, midi_file, verbose=False, debug=False):
        self.verbose = verbose
        self.debug = debug

        self.bytes = -1
        self.headerLength = -1
        self.headerOffset = 23
        self.format = -1
        self.tracks = -1
        self.division = -1
        self.divisionType = -1
        self.itr = 0
        self.runningStatus = -1
        self.tempo = 0

        self.midiRecord_list = []
        self.midi_file = midi_file

        self.deltaTimeStarted = False
        self.deltaTime = 0

        self.key_press_count = 0

        self.startCounter = [0] * len(MidiFile.startSequence)

        self.runningStatusSet = False

        self.events = []
        self.notes = []
        self.success = False

        print("Processing", midi_file)
        try:
            with open(self.midi_file, "rb") as f:
                self.bytes = bytearray(f.read())
            self.readEvents()
            print(self.key_press_count, "notes processed")
            self.clean_notes()
            self.success = True
        finally:
            pass

    def checkStartSequence(self):
        for i in range(len(self.startSequence)):
            if len(self.startSequence[i]) == self.startCounter[i]:
                return True
        return False

    def skip(self, i):
        self.itr += i

    def readLength(self):
        cont_flag = True
        length = 0
        while cont_flag:
            if (self.bytes[self.itr] & 0x80) >> 7 == 0x1:
                length = (length << 7) + (self.bytes[self.itr] & 0x7F)
            else:
                cont_flag = False
                length = (length << 7) + (self.bytes[self.itr] & 0x7F)
            self.itr += 1
        return length

    def readMTrk(self):
        length = self.getInt(4)
        self.log("MTrk len", length)
        self.readMidiTrackEvent(length)

    def readMThd(self):
        self.headerLength = self.getInt(4)
        self.log("HeaderLength", self.headerLength)
        self.format = self.getInt(2)
        self.tracks = self.getInt(2)
        div = self.getInt(2)
        self.divisionType = (div & 0x8000) >> 16
        self.division = div & 0x7FFF
        self.log("Format %d\nTracks %d\nDivisionType %d\nDivision %d" % (self.format, self.tracks, self.divisionType, self.division))

    def readText(self, length):
        s = ""
        start = self.itr
        while self.itr < length + start:
            s += chr(self.bytes[self.itr])
            self.itr += 1
        return s

    def readMidiMetaEvent(self, delta_t):
        midi_type = self.bytes[self.itr]
        self.itr += 1
        length = self.readLength()

        try:
            event_name = self.typeDict[midi_type]
        # Except key not included in dict
        except KeyError:
            event_name = "Unknown Event " + str(midi_type)

        self.log("MIDIMETAEVENT", event_name, "LENGTH", length, "DT", delta_t)
        if midi_type == 0x2F:
            self.log("END TRACK")
            self.itr += 2
            return False
        elif midi_type in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0C]:
            self.log("\t", self.readText(length))
        elif midi_type == 0x51:
            tempo = round(60000000 / self.getInt(3))
            self.tempo = tempo

            self.notes.append([(self.deltaTime / self.division), "tempo=" + str(tempo)])
            self.log("\tNew tempo is", str(tempo))
        else:
            self.itr += length
        return True

    def readMidiTrackEvent(self, length):
        self.log("TRACKEVENT")
        self.deltaTime = 0
        start = self.itr
        continue_flag = True
        while length > self.itr - start and continue_flag:
            delta_t = self.readLength()
            self.deltaTime += delta_t

            if self.bytes[self.itr] == 0xFF:
                self.itr += 1
                continue_flag = self.readMidiMetaEvent(delta_t)
            elif 0xF0 <= self.bytes[self.itr] <= 0xF7:
                self.runningStatusSet = False
                self.runningStatus = -1
                self.log("RUNNING STATUS SET:", "CLEARED")
            else:
                self.readVoiceEvent(delta_t)
        self.log("End of MTrk event, jumping from", self.itr, "to", start + length)
        self.itr = start + length

    def readVoiceEvent(self, delta_t):
        if self.bytes[self.itr] < 0x80 and self.runningStatusSet:
            midi_type = self.runningStatus
            channel = midi_type & 0x0F
        else:
            midi_type = self.bytes[self.itr]
            channel = self.bytes[self.itr] & 0x0F
            if 0x80 <= midi_type <= 0xF7:
                self.log("RUNNING STATUS SET:", hex(midi_type))
                self.runningStatus = midi_type
                self.runningStatusSet = True
            self.itr += 1

        if midi_type >> 4 == 0x9:
            # Key press
            key = self.bytes[self.itr]
            self.itr += 1
            velocity = self.bytes[self.itr]
            self.itr += 1

            # single char
            piano_key = str(key -21)

            if velocity == 0:
                # Spec defines velocity == 0 as an alternate notation for key release
                self.log(self.deltaTime / self.division, "~" + piano_key)
                self.notes.append([(self.deltaTime / self.division), "~" + piano_key])
            else:
                # Real keypress
                self.log(self.deltaTime / self.division, piano_key)
                self.notes.append([(self.deltaTime / self.division), piano_key])
                self.key_press_count += 1

        elif midi_type >> 4 == 0x8:
            # Key release
            key = self.bytes[self.itr]
            self.itr += 1
            velocity = self.bytes[self.itr]
            self.itr += 1

            piano_key = str(key -21)  # Convert from midi to 0-87 scale

            self.log(self.deltaTime / self.division, "~" + piano_key)
            self.notes.append([(self.deltaTime / self.division), "~" + piano_key])

        elif not midi_type >> 4 in [0x8, 0x9, 0xA, 0xB, 0xD, 0xE]:
            self.log("VoiceEvent", hex(midi_type), hex(self.bytes[self.itr]), "DT", delta_t)
            self.itr += 1
        else:
            self.log("VoiceEvent", hex(midi_type), hex(self.bytes[self.itr]), hex(self.bytes[self.itr + 1]), "DT", delta_t)
            self.itr += 2

    def readEvents(self):
        while self.itr + 1 < len(self.bytes):
            # Reset counters to 0
            for i in range(len(self.startCounter)):
                self.startCounter[i] = 0

            # Get to next event / MThd / MTrk
            while self.itr + 1 < len(self.bytes) and not self.checkStartSequence():
                for i in range(len(self.startSequence)):
                    if self.bytes[self.itr] == self.startSequence[i][self.startCounter[i]]:
                        self.startCounter[i] += 1
                    else:
                        self.startCounter[i] = 0

                if self.itr + 1 < len(self.bytes):
                    self.itr += 1

                if self.startCounter[0] == 4:
                    self.readMThd()
                elif self.startCounter[1] == 4:
                    self.readMTrk()

    def log(self, *arg):
        if self.verbose or self.debug:
            for s in range(len(arg)):
                try:
                    print(str(arg[s]), end=" ")
                    self.midiRecord_list.append(str(arg[s]) + " ")
                except:
                    print("[?]", end=" ")
                    self.midiRecord_list.append("[?] ")
            print()
            if self.debug: input()
            self.midiRecord_list.append("\n")
        else:
            for s in range(len(arg)):
                try:
                    self.midiRecord_list.append(str(arg[s]) + " ")
                except:
                    self.midiRecord_list.append("[?] ")
            self.midiRecord_list.append("\n")

    def getInt(self, i):
        k = 0
        for n in self.bytes[self.itr:self.itr + i]:
            k = (k << 8) + n
        self.itr += i
        return k

    def clean_notes(self):
        self.notes = sorted(self.notes, key=lambda note: float(note[0]))

        if self.verbose:
            for x in self.notes:
                print(x)

        # Combine seperate lines with equal timings
        # i = 0
        # while i < len(self.notes) - 1:
        #     a_time, b_time = self.notes[i][0], self.notes[i + 1][0]
        #     if a_time == b_time:
        #         a_notes, b_notes = self.notes[i][1], self.notes[i + 1][1]
        #         if "tempo" not in a_notes and "tempo" not in b_notes and "~" not in a_notes and "~" not in b_notes:
        #             self.notes[i][1] += self.notes[i + 1][1]
        #             self.notes.pop(i + 1)
        #         else:
        #             i += 1
        #     else:
        #         i += 1
        #
        # # Remove duplicate notes on same line
        # for q in range(len(self.notes)):
        #     letter_dict = {}
        #     newline = []
        #     if not "tempo" in self.notes[q][1] and "~" not in self.notes[q][1]:
        #         for i in range(len(self.notes[q][1])):
        #             if not (self.notes[q][1][i] in letter_dict):
        #                 newline.append(self.notes[q][1][i])
        #                 letter_dict[self.notes[q][1][i]] = True
        #         self.notes[q][1] = "".join(newline)
        return

    def save_song(self, song_file):
        print("Saving notes to", song_file)
        with open(song_file, "w") as f:
            f.write("playback_speed=1.0\n")
            for l in self.notes:
                f.write(str(l[0]) + " " + str(l[1]) + "\n")
        return


def get_file_choice():
    file_list = os.listdir("songs")
    mid_list = []
    for f in file_list:
        if ".mid" in f or ".mid" in f.lower():
            mid_list.append(os.path.join("songs", f))
    print("\nType the number of a midi file press enter:\n")
    for i in range(len(mid_list)):
        print(i + 1, ":", mid_list[i])

    choice = int(input(">"))
    print()
    choice_index = int(choice)
    return mid_list[choice_index - 1]


def main():
    import sys
    if len(sys.argv) > 1:
        midi_file = sys.argv[1]
        if not os.path.exists(midi_file):
            print(f"Error: file not found '{midi_file}'")
            return 1

        if not (".mid" in midi_file or ".mid" in midi_file.lower()):
            print(f"'{midi_file}' has an inccorect file extension")
            print("make sure this file ends in '.mid'")
            return 1
    else:
        midi_file = get_file_choice()

    try:
        midi = MidiFile(midi_file)
    except Exception as e:
        print("An error has occured during processing::\n\n")
        raise e

    song_file = "song.txt"

    midi.save_song(song_file)
    print("\nSuccess, playSong is ready to run")
    input("\n\nPress any key to exit...")
    return 0


if __name__ == "__main__":
    main()
