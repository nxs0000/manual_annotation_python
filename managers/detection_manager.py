import numpy as np
import cv2
import json
from datetime import datetime

from services.file_service import open_file


class DetectionManager(object):
    def __init__(self, file, starting_frame=0):
        self.list_detections = {}
        self.list_objects = []

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
        self.color_others = [0, 0, 200]

        self.running = True

        self.alpha = 1.0
        self.beta = 0
        self.gamma = 1.0

        self.frame_reference = None
        self.previous_frame_reference = None
        self.prepare_frame()
        self.h, self.w = self.current_image.shape[:2]

    def save(self, suffix=None, include_current=False):
        file_name = f"./save_{str(datetime.now())[:19].replace(':', '-').replace(' ', '_')}.json"
        if suffix is not None:
            file_name = file_name[:-4] + f"_{suffix}.json"
        else:
            print(f"saving as : {file_name}")

        dict_to_save = self.list_detections.copy()

        if include_current:
            dict_to_save[self.frame_reference] = self.list_objects

        with open(file_name, 'w') as json_file:
            json.dump(dict_to_save, json_file, indent=2)

    def load(self, file_name):
        with open(file_name, 'r') as json_file:
            self.list_detections = json.load(json_file)

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
        if len(self.list_objects) > 0:
            self.list_objects = self.list_objects[:-1]
        elif len(list(self.list_detections)) > 0:
            self.list_objects = self.list_detections[self.previous_frame_reference].copy()
            del self.list_detections[self.previous_frame_reference]
            self.current_frame -= 1
        self.reset_rect()
        self.prepare_frame()
        self.display_frame()

    def next(self, what):
        if what == "object":
            # validate rect
            if self.mouse_drag["end"][0] >= 0 and self.mouse_drag["end"][1] >= 0:
                dict_to_add = {
                    "rect": {
                        "start": (int(self.mouse_drag["start"][0]), int(self.mouse_drag["start"][1])),
                        "end": (int(self.mouse_drag["end"][0]), int(self.mouse_drag["end"][1]))
                    }
                }
                self.list_objects.append(dict_to_add)

                self.reset_rect()
                self.display_frame()
            else:
                return self.next("frame")
        elif what == "frame":
            self.list_detections[self.frame_reference] = self.list_objects.copy()
            self.list_objects = []

            self.reset_rect()

            self.current_frame += 1
            self.prepare_frame()
            self.display_frame()

            if len(list(self.list_detections)) % self.autosave_interval == 0:
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
            elif what.startswith("color_other_"):
                if what[-1] == 'r':
                    self.color_others[2] = value
                elif what[-1] == 'g':
                    self.color_others[1] = value
                elif what[-1] == 'b':
                    self.color_others[0] = value
            self.display_frame()

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
        elif data == 'next object':
            self.next('object')
        elif data == 'next frame':
            self.next('frame')
        elif data == "start_center" and state == 1:
            self.mouse_drag_type = "from_center"
            self.display_frame()
        elif data == "start_top_left" and state == 1:
            self.mouse_drag_type = "from_corner"
            self.display_frame()
        elif data == "display_other":
            self.display_other_points = state == 1
            self.display_frame()

    def force_refresh(self):
        self.prepare_frame()
        self.display_frame()

    def prepare_frame(self):
        frame_idx = self.current_frame
        self.previous_frame_reference = self.frame_reference
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
        frame_idx = self.current_frame

        image_to_show = self.image_for_drawings.copy()

        if self.display_other_points:
            for object in self.list_objects:
                rect = object['rect']
                image_to_show = cv2.rectangle(image_to_show, tuple(rect["start"]),
                                              tuple(rect["end"]), tuple(self.color_others), 1)

        if self.mouse_drag["set"]:
            if self.mouse_drag_type == "from_center" and self.mouse_drag["active"] == "whole_rect":
                start_point = (2 * self.mouse_drag["start"] - self.mouse_drag["end"]).astype(np.int64)
                image_to_show = cv2.rectangle(image_to_show, tuple(start_point), tuple(self.mouse_drag["end"]),
                                              self.color_current, 1)
            else:
                image_to_show = cv2.rectangle(image_to_show, tuple(self.mouse_drag["start"]),
                                              tuple(self.mouse_drag["end"]), tuple(self.color_current), 1)

        cv2.imshow('img', image_to_show)

    def run(self):
        cv2.namedWindow("img", cv2.WINDOW_GUI_NORMAL)
        cv2.setMouseCallback("img", self.mouse_callback)

        cv2.imshow('Controls', np.zeros((10, 400)).astype(np.uint8))

        self.reader.create_gui_options("Controls")

        cv2.createTrackbar("alpha", "Controls", 100, 1000, lambda x: self.track_callback('alpha', x))
        cv2.createTrackbar("beta", "Controls", 0, 255, lambda x: self.track_callback('beta', x))
        cv2.createTrackbar("gamma", "Controls", 100, 200, lambda x: self.track_callback('gamma', x))

        cv2.createTrackbar("current color R", "Controls", self.color_current[2], 255,
                           lambda x: self.track_callback('color_current_r', x))
        cv2.createTrackbar("current color G", "Controls", self.color_current[1], 255,
                           lambda x: self.track_callback('color_current_g', x))
        cv2.createTrackbar("current color B", "Controls", self.color_current[0], 255,
                           lambda x: self.track_callback('color_current_b', x))

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
        cv2.createButton("next object", self.button_callback, "next object", cv2.QT_PUSH_BUTTON)
        cv2.createButton("next frame", self.button_callback, "next frame", cv2.QT_PUSH_BUTTON)

        cv2.createButton("Start drawing rectangle from :", self.button_callback, "", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)
        cv2.createButton("Top left corner", self.button_callback, "start_top_left", cv2.QT_RADIOBOX)
        cv2.createButton("Center", self.button_callback, "start_center", cv2.QT_RADIOBOX, True)

        cv2.createButton("Display other objects", self.button_callback, "display_other", cv2.QT_CHECKBOX | cv2.QT_NEW_BUTTONBAR, True)

        cv2.createButton("quit", self.button_callback, "quit", cv2.QT_PUSH_BUTTON | cv2.QT_NEW_BUTTONBAR)

        self.prepare_frame()
        while self.running:
            self.display_frame()

            key = cv2.waitKey()

            if key == 32:  # SPACE
                self.next('object')
            elif key == 115:  # S
                self.save()
            elif key == 122:  # Z
                self.undo()

        cv2.destroyAllWindows()
