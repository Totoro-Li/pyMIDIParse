from airtest.core.android.touch_methods.base_touch import *
from airtest.core.api import *


def Const(cls):
    @wraps(cls)
    def new_setattr(self, name, value):
        raise Exception('const : {} can not be changed'.format(name))

    cls.__setattr__ = new_setattr
    return cls


@Const
class BlackKeyRelativeRatio(object):  # Up to down, left to right
    VERTICAL = 0.2658
    KEY1_HORIZONTAL = 0.1391
    KEY2_HORIZONTAL = 0.2857
    KEY3_HORIZONTAL = 0.5714
    KEY4_HORIZONTAL = 0.7180
    KEY5_HORIZONTAL = 0.8609
    HORIZONTOAL = [KEY1_HORIZONTAL, KEY2_HORIZONTAL, KEY3_HORIZONTAL, KEY4_HORIZONTAL, KEY5_HORIZONTAL]


@Const
class WhiteKeyRelativeRatio(object):  # Up to down, left to right
    VERTICAL = 0.8006


@Const
class PianoCropBox(object):
    LEFT_UPPER = (244, 805)
    RIGHT_LOWER = (2232, 1128)


@Const
class PianoSetting(object):
    NUM_OF_OCTAVES = 7
    WHITE_KEY_INDEX = [0, 2, 4, 5, 7, 9, 11]
    BLACK_KEY_INDEX = [1, 3, 6, 8, 10]
    SAMPLING_INTERVAL = 0.02


@Const
class _Const(object):
    BlackKeyRelativeRatio = BlackKeyRelativeRatio()
    WhiteKeyRelativeRatio = WhiteKeyRelativeRatio()
    PianoCropBox = PianoCropBox()
    PianoSetting = PianoSetting()


CONST = _Const()


class DeviceSession(object):

    def __init__(self, ip=None):
        super(DeviceSession, self).__init__()
        self.ori_transformer = None
        self.timer = None
        self.ip = ip
        self.id_gen = 0
        self.device = None
        if ip is not None:
            self.connect(ip)

        self.down_event_to_perform = []
        self.down_event_to_revoke = []

        # Touch position on 88-key piano given a note
        self.piano_width = CONST.PianoCropBox.RIGHT_LOWER[0] - CONST.PianoCropBox.LEFT_UPPER[0]
        self.piano_height = CONST.PianoCropBox.RIGHT_LOWER[1] - CONST.PianoCropBox.LEFT_UPPER[1]

        self.octaves_start_end_pixel = []
        self.unit_white_key = self.piano_width / 52
        self.octaves_start_end_pixel.append((0, 0 + 2 * self.unit_white_key))
        full_octave_width = 7 * self.unit_white_key
        start_of_first_full_octave = self.octaves_start_end_pixel[0][1]
        for i in range(0, CONST.PianoSetting.NUM_OF_OCTAVES):
            self.octaves_start_end_pixel.append((start_of_first_full_octave + full_octave_width * i, start_of_first_full_octave + full_octave_width * (i + 1)))
        self.octaves_start_end_pixel.append((self.octaves_start_end_pixel[-1][1], self.piano_width))

        self.set_timer()

    def connect(self, ip):
        self.ip = ip
        self.device = connect_device("Android:///" + ip)
        self.ori_transformer = self.device.touch_proxy.ori_transformer

        return self.device

    def set_timer(self):
        # call timer_callback every 0.1 second
        self.timer = threading.Timer(CONST.PianoSetting.SAMPLING_INTERVAL, self.timer_callback)
        self.timer.start()

    def generate_id_incremental(self):
        self.id_gen = (self.id_gen + 1) % 10
        return self.id_gen

    def disconnect(self):
        self.device.disconnect()

    def is_connected(self):
        return self.device is not None

    def get_resolution(self) -> (int, int):
        """

        :rtype: width, height
        """
        return self.device.get_current_resolution()

    def play_note(self, note):
        # play midi sound
        print(f"Playing note {note}")
        # x, y = self.translate_note_to_real_coordinate(note)
        # touch((x, y), duration=0.1)
        self.down_event_to_perform.append(note)

    def release_note(self, note: list):
        # print("Releasing note %d" % note)
        pass

    def timer_callback(self):
        multitouch_event = []
        if len(self.down_event_to_revoke) > 0:
            for op_id in self.down_event_to_revoke:
                multitouch_event.append(UpEvent(op_id))
            self.down_event_to_revoke = []
        if len(self.down_event_to_perform) > 0:
            for n in self.down_event_to_perform:
                op_id = self.generate_id_incremental()
                multitouch_event.append(DownEvent(self.ori_transformer(self.translate_note_to_real_coordinate(n)), op_id, 40))
                self.down_event_to_revoke.append(op_id)
            self.down_event_to_perform = []
        if len(multitouch_event) > 0:
            device().touch_proxy.perform(multitouch_event)
        self.set_timer()

    @staticmethod
    def get_note_group_and_relative(note) -> (int, int):
        if note < 3:
            return 0, note
        elif note < 87:
            return ((note - 3) // 12 + 1), (note - 3) % 12
        else:
            return 8, 0

    def get_note_position(self, note):
        group, relative = self.get_note_group_and_relative(note)
        if relative in CONST.PianoSetting.WHITE_KEY_INDEX:
            # White key
            x = self.octaves_start_end_pixel[group][0] + self.unit_white_key * (CONST.PianoSetting.WHITE_KEY_INDEX.index(relative) + 0.5)
            y = self.piano_height * CONST.WhiteKeyRelativeRatio.VERTICAL
        else:
            # Black key
            x = self.octaves_start_end_pixel[group][0] + (self.octaves_start_end_pixel[group][1] - self.octaves_start_end_pixel[group][0]) * CONST.BlackKeyRelativeRatio.HORIZONTOAL[CONST.PianoSetting.BLACK_KEY_INDEX.index(relative)]
            y = self.piano_height * CONST.BlackKeyRelativeRatio.VERTICAL
        return x, y

    def translate_note_to_real_coordinate(self, note) -> (float, float):
        relative_x, relative_y = self.get_note_position(note)
        return relative_x + CONST.PianoCropBox.LEFT_UPPER[0], relative_y + CONST.PianoCropBox.LEFT_UPPER[1]


if __name__ == '__main__':
    session = DeviceSession("DVE0220407001089")
    while True:
        key = input("Enter note to play: ")
        touch((session.translate_note_to_real_coordinate(int(key))))
