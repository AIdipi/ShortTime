##장면별로 어떤 id가 있는지 출력해줌 
import numpy as np
import cv2 as cv
import hashlib
import colorsys
from abc import ABC, abstractmethod
from boxmot.utils import logger as LOGGER


class BaseTracker(ABC):
    def __init__(
        self, 
        det_thresh: float = 0.3,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3,
        max_obs: int = 50
    ):
        self.det_thresh = det_thresh
        self.max_age = max_age
        self.max_obs = max_obs
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.per_class_active_tracks = {}

        self.frame_count = 0
        self.active_tracks = []  # This might be handled differently in derived classes
        
        if self.max_age >= self.max_obs:
            LOGGER.warning("Max age > max observations, increasing size of max observations...")
            self.max_obs = self.max_age + 5
            print("self.max_obs", self.max_obs)

    @abstractmethod
    def update(self, dets: np.ndarray, img: np.ndarray, embs: np.ndarray = None) -> np.ndarray:
        raise NotImplementedError("The update method needs to be implemented by the subclass.")

    def id_to_color(self, id: int, saturation: float = 0.75, value: float = 0.95) -> tuple:
        hash_object = hashlib.sha256(str(id).encode())
        hash_digest = hash_object.hexdigest()
        
        hue = int(hash_digest[:8], 16) / 0xffffffff
        
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        
        rgb_255 = tuple(int(component * 255) for component in rgb)
        hex_color = '#%02x%02x%02x' % rgb_255
        rgb = tuple(int(hex_color.strip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        bgr = rgb[::-1]
        
        return bgr

    def plot_box_on_img(self, img: np.ndarray, box: tuple, conf: float, cls: int, id: int) -> np.ndarray:
        thickness = 2
        fontscale = 0.5

        img = cv.rectangle(
            img,
            (int(box[0]), int(box[1])),
            (int(box[2]), int(box[3])),
            self.id_to_color(id),
            thickness
        )
        img = cv.putText(
            img,
            f'id: {int(id)}, conf: {conf:.2f}, c: {int(cls)}',
            (int(box[0]), int(box[1]) - 10),
            cv.FONT_HERSHEY_SIMPLEX,
            fontscale,
            self.id_to_color(id),
            thickness
        )
        return img

    def plot_trackers_trajectories(self, img: np.ndarray, observations: list, id: int) -> np.ndarray:
        for i, box in enumerate(observations):
            trajectory_thickness = int(np.sqrt(float(i + 1)) * 1.2)
            img = cv.circle(
                img,
                (int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)), 
                2,
                color=self.id_to_color(int(id)),
                thickness=trajectory_thickness
            )
        return img

    def plot_results(self, img: np.ndarray, show_trajectories: bool) -> np.ndarray:
        all_ids = set()  # Set to collect all unique IDs

        if self.per_class_active_tracks:
            for k in self.per_class_active_tracks.keys():
                active_tracks = self.per_class_active_tracks[k]
                for a in active_tracks:
                    if a.history_observations:
                        if len(a.history_observations) > 2:
                            box = a.history_observations[-1]
                            img = self.plot_box_on_img(img, box, a.conf, a.cls, a.id)
                            all_ids.add(a.id)  # Collect ID
                            if show_trajectories:
                                img = self.plot_trackers_trajectories(img, a.history_observations, a.id)
        else:
            for a in self.active_tracks:
                if a.history_observations:
                    if len(a.history_observations) > 2:
                        box = a.history_observations[-1]
                        img = self.plot_box_on_img(img, box, a.conf, a.cls, a.id)
                        all_ids.add(a.id)  # Collect ID
                        if show_trajectories:
                            img = self.plot_trackers_trajectories(img, a.history_observations, a.id)

        # Print all collected IDs
        print("Tracked IDs:", all_ids)
        
        return img
