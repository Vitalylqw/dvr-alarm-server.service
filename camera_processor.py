import os
import multiprocessing
import cv2
import numpy as np
import urllib.request
from onvif import ONVIFCamera
import time
from ultralytics import YOLOv10
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import threading
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

MODEL_NANO = YOLOv10('models/nano_10n_st_11.pt')
MODEL_HEAVY = YOLOv10('models/heavy_10m_st_11.pt')
CONF = 0.35
MAX_DET = 1
port = 8899
number_recorded_pictures = 1000

# Ограничение на отправку сообщений

MESSAGE_COOLDOWN = timedelta(minutes=2)


class CameraProcessor(multiprocessing.Process):
    def __init__(self, ip, user, passw, command_queue, response_queue, alarm_queue, alarm_url, area, port=port):
        super().__init__()
        self.ip_suffix = ip
        self.ip = f'192.168.1.{ip}'
        self.port = port
        self.user = user
        self.pswd = passw
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.alarm_queue = alarm_queue
        self.running = multiprocessing.Value('b', True)
        self.save_dir = f'video/camera_{ip}'
        os.makedirs(f'video/{self.save_dir}', exist_ok=True)
        self.model_nano = MODEL_NANO
        self.model_heavy = MODEL_HEAVY
        self.image_counter = 0
        self.last_telegram_message_time = datetime.min
        self.alarm_url = alarm_url
        self.area = area

    def initialize_logger(self):
        self.logger = logging.getLogger(f'CameraProcessor-{self.ip}')
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(f'logs/camera_{self.ip}.log', maxBytes=10240, backupCount=10)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def initialize_camera(self):
        try:
            self.mycam = ONVIFCamera(self.ip, self.port, self.user, self.pswd)
            self.media_service = self.mycam.create_media_service()
            self.profiles = self.media_service.GetProfiles()
            self.token = self.profiles[0].token
            self.snapshot_uri = self.media_service.GetSnapshotUri({'ProfileToken': self.token})
            parsed_url = urlparse(self.snapshot_uri.Uri)
            query_params = parse_qs(parsed_url.query)
            query_params['user'] = self.user
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse(
                (parsed_url.scheme, parsed_url.netloc, parsed_url.path,
                 parsed_url.params, new_query, parsed_url.fragment)
            )
            self.snapshot_uri['Uri'] = new_url
            self.logger.info(f"Camera {self.ip} initialized successfully.")
        except Exception as e:
            self.logger.error(f"Error initializing camera {self.ip}: {e}")
            self.running.value = False

    def get_snapshot(self):
        # image  = Image.open('test_foto.jpg')
        # return np.array(image)
        try:
            # self.logger.debug(f"Getting snapshot from camera {self.ip}")
            response = urllib.request.urlopen(self.snapshot_uri.Uri)
            data = response.read()
            image_array = np.asarray(bytearray(data), dtype="uint8")
            snapshot = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return snapshot
        except Exception as e:
            self.logger.error(f"Error getting snapshot from camera {self.ip}: {e}")
            self.initialize_camera()
            return None

    def process_image(self, image):
        x, y, w, h = self.area
        roi = image[y:y + h, x:x + w]  # Вырезаем область интереса (ROI)
        return roi

    def check_image_with_model(self, image, model, conf, max_det):
        # self.logger.debug(f"check_image_with_model started {self.ip}")
        if self.area:
            image = self.process_image(image)
        try:
            results = model.predict(image, conf=conf, max_det=max_det, stream=True, verbose=False)
            results = next(results)
            return results.summary(), results.plot()
        except Exception as e:
            self.logger.error(f"Error checking image with model: {e}")
            return None, None

    def save_image(self, image, model_name):
        try:
            if self.image_counter > number_recorded_pictures:
                self.image_counter = 0
            self.image_counter += 1
            image_path = os.path.join(self.save_dir, f'{self.ip.split(".")[-1]}_{self.image_counter}_{model_name}.jpg')
            cv2.imwrite(image_path, image)
            self.logger.debug(f"Image saved to {image_path}")
            return image_path
        except Exception as e:
            self.logger.error(f"Error saving image: {e}")
            return None

    def send_alarm_and_notification(self, image, model_name):
        image_path = self.save_image(image, model_name)
        if image_path:
            self.alarm_queue.put(('alarm', self.alarm_url, self.ip_suffix))
            if (datetime.now() - self.last_telegram_message_time) > MESSAGE_COOLDOWN:
                self.response_queue.put(('notification', (image_path, self.ip_suffix)))
                self.last_telegram_message_time = datetime.now()

    def send_current_snapshot(self):
        snapshot = self.get_snapshot()
        if snapshot is not None:
            image_path = os.path.join(self.save_dir, 'current_snapshot.jpg')
            cv2.imwrite(image_path, snapshot)
            return image_path

    def process_snapshot(self):
        snapshot = self.get_snapshot()
        # self.logger.debug(f"Array size snapshot {snapshot.shape}") #TODO удалить
        if snapshot is not None:
            results_nano, nano_snapshot = self.check_image_with_model(snapshot, self.model_nano, CONF, MAX_DET)
            # self.logger.debug(f"results nano {results_nano}") #TODO удалить
            if results_nano:
                # self.save_image(nano_snapshot, 'nano') #TODO удалить
                # self.save_image(snapshot, 'row_nano') #TODO удалить
                results_heavy, heavy_snapshot = self.check_image_with_model(snapshot, self.model_heavy, CONF, MAX_DET)
                if results_heavy:
                    self.save_image(snapshot, 'row_heavy')  # TODO удалить
                    self.send_alarm_and_notification(heavy_snapshot, 'heavy')
                    time.sleep(10)

    def process_queue(self):
        while self.running.value:
            try:
                if not self.command_queue.empty():
                    command = self.command_queue.get()
                    if command == 'request_snapshot':
                        self.logger.debug(
                            f"Processing snapshot request for camera IP suffix: {self.ip_suffix}")
                        patch = self.send_current_snapshot()
                        self.response_queue.put(('snapshot_done', patch))
                    elif command == 'start_camera':
                        data = f'camera, {self.ip_suffix}, already run'
                        self.logger.debug(data)
                        self.response_queue.put(('camera_status', data))
                    elif command == 'stop_camera':
                        data = f'camera, {self.ip_suffix}, camera started shutdown'
                        self.response_queue.put(('camera_status', data))
                        self.running.value = False
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")
            time.sleep(1)

    def run(self):
        self.initialize_logger()
        self.logger.info(f"Process for camera {self.ip} started")
        self.initialize_camera()
        queue_thread = None
        try:
            queue_thread = threading.Thread(target=self.process_queue)
            queue_thread.start()
        except Exception as e:
            self.logger.error(f"Error in queue_thread: {e}")

        while self.running.value:
            try:
                # self.logger.debug(f"Started process_snapshot from camera {self.ip}")
                self.process_snapshot()
                # self.logger.debug(f"process_snapshot from camera {self.ip} completed successfully")
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in process_snapshot: {e}")
        else:
            if queue_thread:
                queue_thread.join()
                self.logger.debug(f"Stop queue_thread from camera {self.ip}")

        self.logger.info(f"Process for camera {self.ip} stopped")
