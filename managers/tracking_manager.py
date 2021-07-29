import numpy as np
import cv2
import json
from datetime import datetime

from services.file_service import open_file


class TrackingManager(object):
    def __init__(self, file, starting_frame=0):
        self.list_cells = []
        self.current_cell_position = {}

        self.reader = open_file(self, file)

        self.starting_frame = starting_frame
        self.current_frame = self.starting_frame
        self.current_image = np.zeros((1,1))
        self.image_for_drawings = np.zeros((1,1))

        self.autosave_interval = 10

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

        self.display_frame_offset = 0

        self.frame_reference = None
        self.prepare_frame()
        self.h, self.w = self.current_image.shape[:2]

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
                if v.get("ref"):
                    dict_for_cell["timestamps"][k]["ref"] = v["ref"]

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
                if v.get("ref"):
                    dict_for_cell["timestamps"][k]["ref"] = v["ref"]

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
            "active": "",
            "set": False,
            "start": np.ones((2), dtype=np.int64) * -1,
            "end": np.ones((2), dtype=np.int64) * -1
        }

    def is_current_rect_valid(self):
        return 0 <= self.mouse_drag["start"][0] < self.mouse_drag["end"][0] and \
               0 <= self.mouse_drag["start"][1] < self.mouse_drag["end"][1]

    def undo(self):
        if self.current_cell_position.get(self.current_frame - 1) is not None:
            del self.current_cell_position[self.current_frame - 1]
            self.current_frame -= 1
        elif len(self.list_cells) > 0:
            self.current_cell_position = self.list_cells[-1]
            self.list_cells = self.list_cells[:-1]
            self.current_frame = max(k for k, _ in self.current_cell_position.items()) + 1
        self.reset_display_offset()
        self.reset_rect()
        self.prepare_frame()
        self.display_frame()
        self.refresh_track_frame()

    def next(self, what):
        if what == "time":
            # validate rect
            if self.mouse_drag["end"][0] >= 0 and self.mouse_drag["end"][1] >= 0:
                dict_to_add = {
                    "ref": self.frame_reference,
                    "rect": {
                        "start": self.mouse_drag["start"],
                        "end": self.mouse_drag["end"]
                    }
                }
                self.current_cell_position[self.current_frame] = dict_to_add

                self.prepare_frame()
                self.current_frame += 1
                self.reset_display_offset()
                self.reset_rect()
                self.refresh_track_frame()
            else:
                return self.next("cell")
        elif what == "cell":
            self.list_cells.append(self.current_cell_position)
            self.current_cell_position = {}
            self.current_frame = self.starting_frame

            self.reset_display_offset()
            self.reset_rect()

            self.prepare_frame()
            self.display_frame()
            self.refresh_track_frame()

            if len(self.list_cells) % self.autosave_interval == 0:
                self.save("autosave")

    def set_autosave_interval(self, interval):
        self.autosave_interval = interval

    def move_corner(self, idx, x, y):
        if idx == 0:
            self.mouse_drag["start"] = np.array([x, y])
        elif idx == 1:
            self.mouse_drag["start"][1] = y
            self.mouse_drag["end"][0] = x
        elif idx == 2:
            self.mouse_drag["start"][0] = x
            self.mouse_drag["end"][1] = y
        elif idx == 3:
            self.mouse_drag["end"] = np.array([x, y])

    def mouse_callback(self, event, x, y, flags, userdata, **kargs):
        if bool(kargs):
            print(f"mouseCallback - Extra arguments {kargs}")

        if event == cv2.EVENT_MOUSEMOVE:
            if flags & cv2.EVENT_FLAG_RBUTTON:
                if self.mouse_drag["active"] == "whole_rect":
                    self.mouse_drag["end"] = np.array([x, y])
                    self.mouse_drag["set"] = True
                elif self.mouse_drag["active"].startswith("corner_"):
                    corner_idx = int(self.mouse_drag["active"][-1])
                    self.move_corner(corner_idx, x, y)

        elif event == cv2.EVENT_RBUTTONUP:
            start_point = None
            if self.mouse_drag["active"] == "whole_rect":
                end_point = np.array([x, y])
                if self.mouse_drag_type == "from_center":
                    start_point = 2 * self.mouse_drag["start"] - end_point
                else:
                    start_point = self.mouse_drag["start"]
            elif len(self.mouse_drag["active"]) > 0 and self.mouse_drag["active"].startswith("corner_"):
                start_point = self.mouse_drag["start"].copy()
                end_point = self.mouse_drag["end"].copy()

            if start_point is not None:
                self.mouse_drag["start"][0] = min(start_point[0], end_point[0])
                self.mouse_drag["start"][1] = min(start_point[1], end_point[1])
                self.mouse_drag["end"][0] = max(start_point[0], end_point[0])
                self.mouse_drag["end"][1] = max(start_point[1], end_point[1])
                self.mouse_drag["active"] = ""

        elif event == cv2.EVENT_RBUTTONDOWN:
            if flags & cv2.EVENT_FLAG_CTRLKEY and self.is_current_rect_valid():
                if self.is_current_rect_valid():
                    if x - self.mouse_drag["start"][0] < self.mouse_drag["end"][0] - x:
                        if y - self.mouse_drag["start"][1] < self.mouse_drag["end"][1] - y:
                            corner_idx = 0
                        else:
                            corner_idx = 2
                    else:
                        if y - self.mouse_drag["start"][1] < self.mouse_drag["end"][1] - y:
                            corner_idx = 1
                        else:
                            corner_idx = 3
                    self.mouse_drag["active"] = f"corner_{corner_idx}"
                    self.move_corner(corner_idx, x, y)
            else:
                self.reset_rect()
                self.mouse_drag["start"] = np.array([x, y])
                self.mouse_drag["active"] = "whole_rect"
        else:
            return
        self.display_frame()

    def track_callback(self, what, value, **kargs):
        if bool(kargs):
            print(f"trackCallback - Extra arguments {kargs}")
        if what == 'frame':
            value -= self.current_frame
            if value == 0:
                self.reset_display_offset()
            else:
                cv2.displayOverlay("img", f"/!\\ Displaying frame {self.current_frame + value} instead of {self.current_frame}", 0)
            self.display_frame_offset = value
            self.prepare_frame()
            self.display_frame()
        if what == 'alpha':
            self.alpha = value * 0.01
            self.prepare_frame()
            self.display_frame()
        if what == 'beta':
            self.beta = value
            self.prepare_frame()
            self.display_frame()
        if what == 'gamma':
            self.gamma = value * 0.01
            self.prepare_frame()
            self.display_frame()
        elif what.startswith("color_"):
            if what.startswith("color_current_"):
                if what[-1] == 'r':
                    self.color_current[2] = value
                elif what[-1] == 'g':
                    self.color_current[1] = value
                elif what[-1] == 'b':
                    self.color_current[0] = value
            elif what.startswith("color_past_"):
                if what[-1] == 'r':
                    self.color_past[2] = value
                elif what[-1] == 'g':
                    self.color_past[1] = value
                elif what[-1] == 'b':
                    self.color_past[0] = value
            elif what.startswith("color_other_"):
                if what[-1] == 'r':
                    self.color_others[2] = value
                elif what[-1] == 'g':
                    self.color_others[1] = value
                elif what[-1] == 'b':
                    self.color_others[0] = value
            self.display_frame()

    def reset_display_offset(self):
        if self.display_frame_offset != 0:
            cv2.displayOverlay("img", "", 1)
        self.display_frame_offset = 0

    def refresh_track_frame(self):
        cv2.setTrackbarMin("frame offset", "Controls", max(0, self.current_frame - 20))
        cv2.setTrackbarMax("frame offset", "Controls", min(self.reader.get_frame_count(), self.current_frame + 20))
        cv2.setTrackbarPos("frame offset", "Controls", self.current_frame)

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
            exit(0)
        elif data == 'time':
            self.next('time')
        elif data == 'cell':
            self.next('cell')
        elif data == "start_center" and state == 1:
            self.mouse_drag_type = "from_center"
            self.display_frame()
        elif data == "start_top_left" and state == 1:
            self.mouse_drag_type = "from_corner"
            self.display_frame()
        elif data == "reset_frame_offset":
            self.reset_display_offset()
            self.refresh_track_frame()
            self.prepare_frame()
            self.display_frame()
        elif data == "display_other":
            self.display_other_points = state == 1
            self.display_frame()
        elif data == "display_past":
            self.display_current_points = state == 1
            self.display_frame()

    def force_refresh(self):
        self.prepare_frame()
        self.display_frame()

    def prepare_frame(self):
        frame_idx = self.current_frame + self.display_frame_offset
        image, self.frame_reference = self.reader.get_frame(frame_idx)

        self.current_image = image.copy()
        if len(image.shape) == 2:
            self.current_image = cv2.cvtColor(self.current_image, cv2.COLOR_GRAY2BGR)

        self.image_for_drawings = np.clip(
            ((((self.current_image.astype(np.float64) / 255.) ** self.gamma) * 255.) * self.alpha + self.beta),
            0,
            255
        ).astype(np.uint8)

    def display_frame(self):
        frame_idx = self.current_frame + self.display_frame_offset

        image_to_show = self.image_for_drawings.copy()

        if self.display_other_points:
            for cell in self.list_cells:
                if cell.get(frame_idx) is not None:
                    cell_dict = cell.get(frame_idx)
                    rect = cell_dict['rect']
                    image_to_show = cv2.rectangle(image_to_show, tuple(rect["start"]),
                                                  tuple(rect["end"]), tuple(self.color_others), 1)

        if self.display_current_points:
            for i in range(0, 4):
                if self.current_cell_position.get(frame_idx - i - 1) is not None:
                    last_dict = self.current_cell_position.get(frame_idx - i - 1)
                    rect = last_dict['rect']
                    image_to_show = cv2.rectangle(image_to_show, tuple(rect["start"]),
                                                  tuple(rect["end"]), tuple(self.color_past), 1)

        if self.mouse_drag["set"]:
            if self.mouse_drag_type == "from_center" and self.mouse_drag["active"] == "whole_rect":
                start_point = (2 * self.mouse_drag["start"] - self.mouse_drag["end"]).astype(np.int64)
                image_to_show = cv2.rectangle(image_to_show, tuple(start_point), tuple(self.mouse_drag["end"]),
                                              self.color_current, 1)
            else:
                image_to_show = cv2.rectangle(image_to_show, tuple(self.mouse_drag["start"]),
                                              tuple(self.mouse_drag["end"]), tuple(self.color_current), 1)

        cv2.imshow('img', image_to_show)
        cv2.imshow('Controls', np.zeros((10, 400)).astype(np.uint8))

    def run(self):
        cv2.namedWindow("img", cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback("img", self.mouse_callback)
        cv2.imshow('Controls', np.zeros((10, 400)).astype(np.uint8))

        self.reader.create_gui_options("Controls")

        cv2.createTrackbar("frame offset", "Controls", 0, self.reader.get_frame_count(), lambda x: self.track_callback('frame', x))
        cv2.createTrackbar("alpha", "Controls", 100, 1000, lambda x: self.track_callback('alpha', x))
        cv2.createTrackbar("beta", "Controls", 0, 255, lambda x: self.track_callback('beta', x))
        cv2.createTrackbar("gamma", "Controls", 100, 200, lambda x: self.track_callback('gamma', x))

        cv2.createTrackbar("current color R", "Controls", self.color_current[2], 255,
                           lambda x: self.track_callback('color_current_r', x))
        cv2.createTrackbar("current color G", "Controls", self.color_current[1], 255,
                           lambda x: self.track_callback('color_current_g', x))
        cv2.createTrackbar("current color B", "Controls", self.color_current[0], 255,
                           lambda x: self.track_callback('color_current_b', x))

        cv2.createTrackbar("past color R", "Controls", self.color_past[2], 255,
                           lambda x: self.track_callback('color_past_r', x))
        cv2.createTrackbar("past color G", "Controls", self.color_past[1], 255,
                           lambda x: self.track_callback('color_past_g', x))
        cv2.createTrackbar("past color B", "Controls", self.color_past[0], 255,
                           lambda x: self.track_callback('color_past_b', x))

        cv2.createTrackbar("others color R", "Controls", self.color_others[2], 255,
                           lambda x: self.track_callback('color_other_r', x))
        cv2.createTrackbar("others color G", "Controls", self.color_others[1], 255,
                           lambda x: self.track_callback('color_other_g', x))
        cv2.createTrackbar("others color B", "Controls", self.color_others[0], 255,
                           lambda x: self.track_callback('color_other_b', x))
        # cv2.namedWindow('Interface')
        cv2.createButton("save", self.button_callback, "save", cv2.QT_PUSH_BUTTON)
        cv2.createButton("save (include current)", self.button_callback, "save_include", cv2.QT_PUSH_BUTTON)
        cv2.createButton("undo", self.button_callback, "undo", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)
        cv2.createButton("next time", self.button_callback, "time", cv2.QT_PUSH_BUTTON)
        cv2.createButton("next cell", self.button_callback, "cell", cv2.QT_PUSH_BUTTON)

        cv2.createButton("reset frame display offset", self.button_callback, "reset_frame_offset", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)

        cv2.createButton("Start drawing rectangle from :", self.button_callback, "", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)
        cv2.createButton("Top left corner", self.button_callback, "start_top_left", cv2.QT_RADIOBOX)
        cv2.createButton("Center", self.button_callback, "start_center", cv2.QT_RADIOBOX, True)

        cv2.createButton("Display other objects", self.button_callback, "display_other", cv2.QT_CHECKBOX | cv2.QT_NEW_BUTTONBAR, True)
        cv2.createButton("Display past positions", self.button_callback, "display_past", cv2.QT_CHECKBOX, True)

        cv2.createButton("quit", self.button_callback, "quit", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)

        self.prepare_frame()
        while self.running:
            self.display_frame()

            key = cv2.waitKey()

            if key == 32:  # SPACE
                self.next('time')
            elif key == 115:  # S
                self.save()
            elif key == 122:  # Z
                self.undo()

        cv2.destroyAllWindows()
