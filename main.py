import os

from managers.detection_manager import DetectionManager
from managers.tracking_manager import TrackingManager

"""

--- After starting, select 'Controls' window and press ctrl+p ---

- Right click and drag to draw rectangles
- CTRL + Right click to move closest corner
- Space to validate current rectangle and move on to the next frame
- Space without drawing new rectangle to move en to the next object to track from the beginning
- S to save all validated objects
- Z to undo last rectangle

"""


if __name__ == '__main__':

    input_file = input('Path to the file/folder : ')
    if not os.path.isfile(input_file) or not os.path.isdir(input_file):
        print(f'Given path is not a file nor directory')
        exit(1)

    print('')
    print('--- After starting, select \'Controls\' window and press ctrl+p ---')
    print('')
    print('- Right click and drag to draw rectangles')
    print('- CTRL + Right click to move closest corner')
    print('- Space to validate current rectangle and move on to the next frame')
    print('- Space without drawing new rectangle to move en to the next object to track from the begining')
    print('- S to save all validated objects')
    print('- Z to undo last rectangle')

    detector = DetectionManager(input_file)
    detector.run()
