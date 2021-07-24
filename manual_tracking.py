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
        self.image_for_drawings = self.current_image.copy()
        
        self.autosave_interval = 10
        
        self.h, self.w = self.images[0].shape
        
        self.display_current_points = True
        self.display_other_points = True

        self.mouse_drag_type = "from_center"
        self.mouse_drag = {}
        self.reset_rect()

        self.color_current = [200, 0, 0]
        self.color_past = [0, 100, 0]
        self.color_others = [0, 0, 200]

        self.running = True

        self.alpha = 1.0
        self.beta = 0
        self.gamma = 1.0

    def save(self, suffix=None, include_current=False):
        file_name = f"./save_{str(datetime.now())[:19].replace(':', '-').replace(' ', '_')}.json"
        if suffix is not None:
            file_name = file_name[:-4] + f"_{suffix}.json"
        else:
            print(f"saving as : {file_name}")

        list_to_save = []
        for cell_idx in range(len(self.list_cells)):
            cell = self.list_cells[cell_idx]
            dict_for_cell = {
                "id": cell_idx,
                "timestamps": {}
            }

            for k, v in cell.items():
                dict_for_cell["timestamps"][k] = {
                    "rect": {
                        'start': (int(v['rect']['start'][0]), int(v['rect']['start'][1])),
                        'end': (int(v['rect']['end'][0]), int(v['rect']['end'][1])),
                    }
                }

            list_to_save.append(dict_for_cell)

        if include_current:
            dict_for_cell = {
                "id": len(list_to_save),
                "timestamps": {}
            }

            for k, v in self.current_cell_position.items():
                dict_for_cell["timestamps"][k] = {
                    "rect": {
                        'start': (int(v['rect']['start'][0]), int(v['rect']['start'][1])),
                        'end': (int(v['rect']['end'][0]), int(v['rect']['end'][1])),
                    }
                }

            list_to_save.append(dict_for_cell)

        with open(file_name, 'w') as json_file:
            json.dump(list_to_save, json_file, indent=4)

    def load(self, file_name):
        with open(file_name, 'r') as json_file:
            data = json.load(json_file)
            for el in data:
                cell = {int(k): v for k, v in el.items()}
                self.list_cells.append(cell)

    def reset_rect(self):
        self.mouse_drag = {
            "active": False,
            "set": False,
            "start": np.ones((2), dtype=np.int64)*-1,
            "end": np.ones((2), dtype=np.int64)*-1
        }

    def undo(self):
        if self.current_cell_position.get(self.current_frame - 1) is not None:
            del self.current_cell_position[self.current_frame - 1]
            self.current_frame -= 1
        elif len(self.list_cells) > 0:
            self.current_cell_position = self.list_cells[-1]
            self.list_cells = self.list_cells[:-1]
            self.current_frame = max(k for k, _ in self.current_cell_position.items()) + 1
        self.reset_rect()
        self.prepare_frame()
        self.displayFrame()

    def next(self, type):
        if type == "time":
            # validate rect
            if self.mouse_drag["end"][0] >= 0 and self.mouse_drag["end"][1] >= 0:
                dict_to_add = {
                    "rect": {
                        "start": self.mouse_drag["start"] if self.mouse_drag_type != "from_center" else 2 * self.mouse_drag["start"] - self.mouse_drag["end"],
                        "end": self.mouse_drag["end"]
                    }
                }
                # print(f'validating {dict_to_add}')
                self.current_cell_position[self.current_frame] = dict_to_add

                self.prepare_frame()
                self.current_frame += 1
                self.reset_rect()
            else:
                return self.next("cell")
        elif type == "cell":
            print(f'next cell')
            self.list_cells.append(self.current_cell_position)
            self.current_cell_position = {}
            self.current_frame = 0
            self.reset_rect()

            self.prepare_frame()
            self.displayFrame()

            if len(self.list_cells) % self.autosave_interval == 0:
                self.save("autosave")

    def set_autosave_interval(self, interval):
        self.autosave_interval = interval
    
    def mouseCallback(self, event, x, y, flags, userdata, **kargs):
        if bool(kargs):
            print(f"mouseCallback - Extra arguments {kargs}")

        if event == cv2.EVENT_MOUSEMOVE:
            if flags & cv2.EVENT_FLAG_RBUTTON:
                # move during rectangle draw
                if self.mouse_drag["active"]:
                    # print("mouse r pressed and move")
                    self.mouse_drag["end"] = np.array([x, y])
                    self.mouse_drag["set"] = True
        elif event == cv2.EVENT_RBUTTONUP:
            if self.mouse_drag["start"][0] >= 0:
                self.mouse_drag["end"] = np.array([x, y])
            self.mouse_drag["active"] = False
        elif event == cv2.EVENT_RBUTTONDOWN:
            self.reset_rect()
            self.mouse_drag["start"] = np.array([x, y])
            self.mouse_drag["active"] = True
        else:
            return
        self.displayFrame()

    def trackCallback(self, id, value, **kargs):
        if bool(kargs):
            print(f"trackCallback - Extra arguments {kargs}")
        if id == 'frame':
            self.displayFrame(value)
        if id == 'alpha':
            self.alpha = value * 0.01
            self.prepare_frame()
            self.displayFrame()
        if id == 'beta':
            self.beta = value
            self.prepare_frame()
            self.displayFrame()
        if id == 'gamma':
            self.gamma = value * 0.01
            self.prepare_frame()
            self.displayFrame()
        elif id.startswith("color_"):
            if id.startswith("color_current_"):
                if id[-1] == 'r':
                    self.color_current[2] = value
                elif id[-1] == 'g':
                    self.color_current[1] = value
                elif id[-1] == 'b':
                    self.color_current[0] = value
            elif id.startswith("color_past_"):
                if id[-1] == 'r':
                    self.color_past[2] = value
                elif id[-1] == 'g':
                    self.color_past[1] = value
                elif id[-1] == 'b':
                    self.color_past[0] = value
            elif id.startswith("color_other_"):
                if id[-1] == 'r':
                    self.color_others[2] = value
                elif id[-1] == 'g':
                    self.color_others[1] = value
                elif id[-1] == 'b':
                    self.color_others[0] = value
            self.displayFrame()

    def button_callback(self, state, data, **kargs):
        if bool(kargs):
            print(f"button_callback - Extra arguments {kargs}")
        if data == "save":
            self.save()
        elif data == 'save_include':
            self.save(include_current=True)
        elif data == "undo":
            self.undo()
        elif data == "quit":
            self.save("onquit")
            self.running = False
        elif data == 'time':
            self.next('time')
        elif data == 'cell':
            self.next('cell')
        elif data == "start_center" and state == 1:
            self.mouse_drag_type = "from_center"
            self.displayFrame()
        elif data == "start_top_left" and state == 1:
            self.mouse_drag_type = "from_corner"
            self.displayFrame()

    def prepare_frame(self):
        self.current_image = cv2.cvtColor(self.images[self.current_frame], cv2.COLOR_GRAY2BGR)

        self.image_for_drawings = np.clip(
            ((((self.current_image.astype(np.float64) / 255.) ** self.gamma) * 255.) * self.alpha + self.beta),
            0,
            255
        ).astype(np.uint8)

    def displayFrame(self, specific_t=None):
        f = self.current_frame
        # if specific_t is not None:
        #     f += specific_t
        # f = min(f, len(self.images))
        
        # self.current_image = cv2.cvtColor(self.images[f], cv2.COLOR_GRAY2BGR)
        #
        # self.current_image = np.clip(
        #     ((((self.current_image.astype(np.float64) / 255.)**self.gamma)*255.) * self.alpha + self.beta),
        #     0,
        #     255
        # ).astype(np.uint8)

        image_to_show = self.image_for_drawings.copy()

        if self.display_other_points:
            for cell in self.list_cells:
                if cell.get(f) is not None:
                    cell_dict = cell.get(f)
                    rect = cell_dict['rect']
                    image_to_show = cv2.rectangle(image_to_show, tuple(rect["start"]),
                                                       tuple(rect["end"]), tuple(self.color_others), 1)

        if self.display_current_points:
            for i in range(0, 4):
                if self.current_cell_position.get(f-i-1) is not None:
                    last_dict = self.current_cell_position.get(f-i-1)
                    rect = last_dict['rect']
                    image_to_show = cv2.rectangle(image_to_show, tuple(rect["start"]),
                                                       tuple(rect["end"]), tuple(self.color_past), 1)

        if self.mouse_drag["set"]:
            if self.mouse_drag_type == "from_center":
                start_point = 2 * self.mouse_drag["start"] - self.mouse_drag["end"]
                image_to_show = cv2.rectangle(image_to_show, tuple(start_point), tuple(self.mouse_drag["end"]), self.color_current, 1)
            else:
                image_to_show = cv2.rectangle(image_to_show, tuple(self.mouse_drag["start"]), tuple(self.mouse_drag["end"]), tuple(self.color_current), 1)
        
        cv2.imshow('img', image_to_show)
        cv2.imshow('scroll', np.zeros((10, 400)).astype(np.uint8))
        
    def run(self):
        cv2.namedWindow("img", cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback("img", self.mouseCallback)
        cv2.imshow('scroll', np.zeros((10, 400)).astype(np.uint8))
        # cv2.createTrackbar("frame offset", "scroll", 0, len(self.images), lambda x: self.trackCallback('frame', x))
        cv2.createTrackbar("alpha", "scroll", 100, 1000, lambda x: self.trackCallback('alpha', x))
        cv2.createTrackbar("beta", "scroll", 0, 255, lambda x: self.trackCallback('beta', x))
        cv2.createTrackbar("gamma", "scroll", 100, 200, lambda x: self.trackCallback('gamma', x))

        cv2.createTrackbar("current color R", "scroll", self.color_current[2], 255, lambda x: self.trackCallback('color_current_r', x))
        cv2.createTrackbar("current color G", "scroll", self.color_current[1], 255, lambda x: self.trackCallback('color_current_g', x))
        cv2.createTrackbar("current color B", "scroll", self.color_current[0], 255, lambda x: self.trackCallback('color_current_b', x))

        cv2.createTrackbar("past color R", "scroll", self.color_past[2], 255, lambda x: self.trackCallback('color_past_r', x))
        cv2.createTrackbar("past color G", "scroll", self.color_past[1], 255, lambda x: self.trackCallback('color_past_g', x))
        cv2.createTrackbar("past color B", "scroll", self.color_past[0], 255, lambda x: self.trackCallback('color_past_b', x))

        cv2.createTrackbar("others color R", "scroll", self.color_others[2], 255, lambda x: self.trackCallback('color_other_r', x))
        cv2.createTrackbar("others color G", "scroll", self.color_others[1], 255, lambda x: self.trackCallback('color_other_g', x))
        cv2.createTrackbar("others color B", "scroll", self.color_others[0], 255, lambda x: self.trackCallback('color_other_b', x))
        # cv2.namedWindow('Interface')
        cv2.createButton("save", self.button_callback, "save", cv2.QT_PUSH_BUTTON)
        cv2.createButton("save (include current)", self.button_callback, "save_include", cv2.QT_PUSH_BUTTON)
        cv2.createButton("undo", self.button_callback, "undo", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)
        cv2.createButton("next time", self.button_callback, "time", cv2.QT_PUSH_BUTTON)
        cv2.createButton("next cell", self.button_callback, "cell", cv2.QT_PUSH_BUTTON)

        cv2.createButton("start top left", self.button_callback, "start_top_left", cv2.QT_RADIOBOX | cv2.QT_NEW_BUTTONBAR)
        cv2.createButton("start center", self.button_callback, "start_center", cv2.QT_RADIOBOX)

        cv2.createButton("quit", self.button_callback, "quit", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)

        print('--- After starting, select \'scroll\' window and press ctrl+p ---')

        self.prepare_frame()
        while self.running:
            self.displayFrame()

            key = cv2.waitKey()
            
            if key == 32:  # SPACE
                self.next('time')
            elif key == 115:  # S
                self.save()
            elif key == 122:  # Z
                self.undo()

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
    tracker.run()



