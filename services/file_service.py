import os

from readers.folder_reader import FolderReader
from readers.tiff_reader import TiffReader


def open_file(caller, path):
    if os.path.isdir(path):
        return FolderReader(caller, path)
    elif os.path.isfile(path):
        if path[-4:] == '.tif' or path[-5:] == '.tiff':
            return TiffReader(caller, path)
