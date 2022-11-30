import mido


def midi_note_to_piano_key(note):
    #     Piano key ranges from 0 to 87
    return note - 21


def sort_notes_by_pitch(notes):
    return sorted(notes, key=lambda note: note[1])


if __name__ == "__main__":
    mid = mido.MidiFile("../songs/Vivaldis_Spring_from_the_Four_Seasons_Piano_Transcription.mid")
