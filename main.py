import os
from dotenv import load_dotenv
import multiprocessing
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from camera_processor import CameraProcessor
from telegram_processor import TelegramBotProcessor
from alarm_processor import AlarmProcessor


# Ограничение на отправку сообщений
last_telegram_message_time = datetime.min
MESSAGE_COOLDOWN = timedelta(minutes=10)
valid_camera_params = ['ip', 'user', 'passw',
                       'command_queue', 'response_queue',
                       'alarm_queue', 'alarm_url', 'area', 'port']


def load_configuration():
    # Загрузка переменных окружения
    load_dotenv()

    # Телеграм-бот настройки
    global TELEGRAM_BOT_TOKEN, CHAT_ID, camera_ips
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
    camera_ips = os.getenv('camera_ips')
    camera_ips = eval(os.getenv('CAMERA_IPS'))


def initialize_main_logger():
    logger = logging.getLogger('Main')
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler('logs/main.log', maxBytes=10240, backupCount=10)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def clear_queue(queue):
    while not queue.empty():
        try:
            queue.get_nowait()
        except:
            continue


def main():
    logger = initialize_main_logger()
    logger.info("Starting main function")

    with multiprocessing.Manager() as manager:
        command_queue = {}
        response_queue = manager.Queue()
        alarm_queue = manager.Queue()
        load_configuration()
        alarm_process = AlarmProcessor(alarm_queue, response_queue)
        alarm_process.start()
        logger.info("Alarm process started")

        camera_processes = []

        def initializing_camera(camera):
            ip = camera['ip']
            camera_ip = f'192.168.1.{ip}'
            logger.info(f"Initializing camera {camera_ip}")
            check_command_queue = command_queue.get(ip, None)
            command_queue[ip] = check_command_queue if check_command_queue else manager.Queue()
            camera_params = {k: v for k, v in camera.items() if
                             k in valid_camera_params}
            camera_process = CameraProcessor(command_queue=command_queue[ip],
                                             response_queue=response_queue,
                                             alarm_queue=alarm_queue,
                                             **camera_params)
            camera_process.start()
            camera_processes.append(camera_process)
            logger.info(f"Camera {camera_ip} started successfully")

        def find_camera(ip_suffix):
            for camera in camera_ips:
                if camera['ip'] == ip_suffix:
                    return camera
            return None

        for camera in camera_ips:
            if camera['track']:
                initializing_camera(camera)
        main_queue = manager.Queue()
        command_queue['main'] = main_queue
        telegram_bot_process = TelegramBotProcessor(TELEGRAM_BOT_TOKEN,
                                                    CHAT_ID, command_queue,
                                                    response_queue)
        telegram_bot_process.start()
        logger.info("Telegram bot process started")

        try:
            while telegram_bot_process.running.value:
                if not main_queue.empty():
                    response = main_queue.get()
                    if isinstance(response, tuple) and len(response) == 2:
                        command, data = response
                        if command == 'start_camera':
                            camera = find_camera(data)
                            if camera:
                                initializing_camera(camera)
                                logger.info(
                                    f"Camera process {data} started")
                    else:
                        logger.error(
                            f"Error start_camera. Can not parse response: {command_queue}")
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, shutting down")
        finally:
            for process in camera_processes:
                process.running.value = False
                process.join()
                logger.info(f"Camera process {process.ip} joined")
            telegram_bot_process.running.value = False
            telegram_bot_process.join()
            logger.info("Telegram bot process joined")

            alarm_process.running.value = False
            alarm_process.join()
            logger.info("Alarm process joined")

    logger.info("Main function finished")


if __name__ == '__main__':
    main()

