

class BaseReader(object):
    def __init__(self, caller, path_to_file):

        self.caller = caller

    def get_frame(self, idx):
        pass

    def get_frame_count(self):
        pass

    def signal_from_gui(self, **kargs):
        pass

    def create_gui_options(self, window_name):
        pass
