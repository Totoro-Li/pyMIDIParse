import mido


def midi_note_to_piano_key(note):
    #     Piano key ranges from 0 to 87
    return note - 21


if __name__ == "__main__":
    mid = mido.MidiFile("songs/Chopin - Nocturne op.9 No.2.mid")
    scores = []  # (time, piano converted note)
    for msg in mid.play():
        if msg.type == "note_on":
            print((msg.time, midi_note_to_piano_key(msg.note)))
