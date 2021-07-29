import os
import cv2

from readers.base_reader import BaseReader


class FolderReader(BaseReader):
    def __init__(self, caller, path_to_folder):
        super().__init__(caller, path_to_folder)

        self.path_to_folder = path_to_folder
        self.all_files = os.listdir(path_to_folder)
        self.all_files = [file for file in self.all_files if file[-4:] == '.jpg' or file[-4:] == '.png' or file[-4:] == '.tif']

    def get_frame(self, idx):
        file_name = self.all_files[idx]
        path_to_file = os.path.join(self.path_to_folder, file_name)
        img = cv2.imread(path_to_file)
        return img, file_name[:file_name.rfind(".")]

    def get_frame_count(self):
        return len(self.all_files)

    def signal_from_gui(self, what, **kargs):
        pass

    def create_gui_options(self, window_name):
        pass
