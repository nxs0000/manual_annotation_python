import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
import json
from datetime import datetime


class ManualTracker():
    def __init__(self, file, starting_frame=0):
        self.list_cells = []
        self.current_cell_position = {}
        
        self.reset_signal = False
        
        ret, self.images = cv2.imreadmulti(file)[starting_frame:]
        self.starting_frame = starting_frame
        self.current_frame = self.starting_frame
        self.current_image = self.images[self.current_frame]
        
        self.autosave_interval = 10
        
        self.h, self.w = self.images[0].shape
        
        self.display_current_points = True
        self.display_other_points = True

    def save(self, suffix=None):
        file_name = f"./save_{str(datetime.now())[:19].replace(':', '-').replace(' ', '_')}.json"
        if suffix is not None:
            file_name = file_name[:-4] + f"_{suffix}.json"
        else:
            print(f"saving as : {file_name}")
        with open(file_name, 'w') as json_file:
            json.dump(self.list_cells, json_file)

    def load(self, file_name):
        with open(file_name, 'r') as json_file:
            data = json.load(json_file)
            for el in data:
                cell = {int(k): v for k, v in el.items()}
                self.list_cells.append(cell)

    def set_autosave_interval(self, interval):
        self.autosave_interval = interval
    
    def mouseCallback(self, event, x, y, flags, userdata, **kargs):
        if bool(kargs):
            print(f"mouseCallback - Extra arguments {kargs}")
        if (event & 1) and (flags & 2):
            self.reset_signal = False
            self.current_cell_position[self.current_frame] = [x, y]
            self.current_frame += 1
            self.displayFrame()

    def trackCallback(self, pos, **kargs):
        if bool(kargs):
            print(f"trackCallback - Extra arguments {kargs}")
        self.displayFrame(pos)

    def saveButtonCallback(self, state, data, **kargs):
        if bool(kargs):
            print(f"saveButtonCallback - Extra arguments {kargs}")

    def displayFrame(self, specific_t=None):
        f = self.current_frame
        if specific_t is not None:
            f += specific_t
        f = min(f, len(self.images))
        
        self.current_image = cv2.cvtColor(self.images[f], cv2.COLOR_GRAY2BGR)
        
        if self.display_other_points:
            for cell in self.list_cells:
                if cell.get(f) is not None:
                    coords = cell.get(f)
                    self.current_image[coords[1], max(0, coords[0]-1):min(self.w-1, coords[0]+2)] = (0, 0, 200)
                    self.current_image[max(0, coords[1]-1):min(self.h-1, coords[1]+2), coords[0]] = (0, 0, 200)
        
        if self.display_current_points:
            for i in range(1, 4):
                if self.current_cell_position.get(f-i-1) is not None:
                    coords = self.current_cell_position.get(f-i-1)
                    self.current_image[coords[1], max(0, coords[0]-1):min(self.w-1, coords[0]+2)] = (0, 150, 0)
                    self.current_image[max(0, coords[1]-1):min(self.h-1, coords[1]+2), coords[0]] = (0, 150, 0)
            
            if f > 0:
                if self.current_cell_position.get(f-1) is not None:
                    last_coords = self.current_cell_position[f-1]
                    self.current_image[last_coords[1], max(0, last_coords[0]-1):min(self.w-1, last_coords[0]+2)] = (200, 0, 0)
                    self.current_image[max(0, last_coords[1]-1):min(self.h-1, last_coords[1]+2), last_coords[0]] = (200, 0, 0)
        
        cv2.imshow('img', self.current_image)
        cv2.imshow('scroll', np.zeros((10, 400)).astype(np.uint8))
        
    def run(self):
        cv2.namedWindow("img", cv2.WINDOW_GUI_NORMAL)
        while True:
            self.displayFrame()
            cv2.setMouseCallback("img", self.mouseCallback)
            cv2.createTrackbar("frame", "scroll", 0, len(self.images), self.trackCallback)

            key = cv2.waitKey()
            
            if key == 115:  # S
                self.save()
            elif key == 122:  # Z
                if self.current_cell_position.get(self.current_frame-1) is not None:
                    del self.current_cell_position[self.current_frame-1]
                    self.current_frame -= 1
                    continue
                elif len(self.current_cell_position) == 0:
                    self.current_cell_position = self.list_cells[-1]
                    self.list_cells = self.list_cells[:-1]
                    self.current_frame = max(k for k, _ in self.current_cell_position.items())+1
            elif self.reset_signal:
                self.save("onquit")
                break
            else:
                self.reset_signal = True
                self.list_cells.append(self.current_cell_position)
                self.current_cell_position = {}
                self.current_frame = self.starting_frame
                
                if len(self.list_cells) % self.autosave_interval == 0:
                    self.save("autosave")
        
        cv2.destroyAllWindows()


if __name__ == '__main__':

    input_file = input('Path to the file : ')
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

    tracker = ManualTracker(input_file, start_frame)
    #tracker.load("save_2021-04-03_20-33-55.json")
    #tracker.display_current_points = True
    tracker.run()



