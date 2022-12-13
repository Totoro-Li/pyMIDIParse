from music21 import *

if __name__ == '__main__':
    mxl = converter.parse("songs/青花瓷 (Blue and White Porcelain).mxl")

    # Split left and right hand
    left_hand = mxl.parts[0]
    right_hand = mxl.parts[1]

    left_hand.show('midi')
