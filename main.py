import os

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
    if not os.path.isfile(input_file):
        print(f'Given path is not a file')
        exit(1)
    start_frame = input('Start at frame (default 0): ')
    try:
        if len(start_frame) != 0:
            start_frame = 0
        else:
            start_frame = int(start_frame)
    except:
        start_frame = 0

    print('')
    print('--- After starting, select \'Controls\' window and press ctrl+p ---')
    print('')
    print('- Right click and drag to draw rectangles')
    print('- CTRL + Right click to move closest corner')
    print('- Space to validate current rectangle and move on to the next frame')
    print('- Space without drawing new rectangle to move en to the next object to track from the begining')
    print('- S to save all validated objects')
    print('- Z to undo last rectangle')

    tracker = TrackingManager(input_file, start_frame)
    tracker.run()
