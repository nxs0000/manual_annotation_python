import cv2

from readers.base_reader import BaseReader


class TiffReader(BaseReader):
    def __init__(self, caller, path_to_file):
        super().__init__(caller, path_to_file)

        _, self.all_frames = cv2.imreadmulti(path_to_file)

        self.channels_count = 1
        # self.depth_count = 1

        self.channel_to_show = 0
        # self.depth_to_show = 0

        self.convert_to_rgb = False

    def get_frame(self, idx):
        timestamps = idx * self.channels_count
        return self.all_frames[timestamps], f'timestamp_{idx}'

    def get_frame_count(self):
        return len(self.all_frames) // self.channels_count

    def signal_from_gui(self, what, **kargs):
        if what == 'channels_count':
            self.channels_count = int(kargs['value'][0])
            self.caller.force_refresh()
        pass

    def create_gui_options(self, window_name):
        cv2.createTrackbar("Amount of channels", window_name, 1, 4,
                           lambda *x: self.signal_from_gui(what='channels_count', value=x))
        cv2.setTrackbarMin("Amount of channels", window_name, 1)
        cv2.setTrackbarMax("Amount of channels", window_name, 4)
