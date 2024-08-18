from logging.handlers import RotatingFileHandler
import asyncio
import aiohttp
import multiprocessing
import logging

class AlarmProcessor(multiprocessing.Process):
    def __init__(self, alarm_queue, response_queue):
        super().__init__()
        self.alarm_queue = alarm_queue
        self.response_queue = response_queue
        self.running = multiprocessing.Value('b', True)

    def initialize_logger(self):
        self.logger = logging.getLogger('AlarmProcessor')
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler('logs/alarm.log', maxBytes=10240, backupCount=10)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def send_alarm(self, alarm_url, ip_suffix):
        if alarm_url:
            try:
                self.logger.debug(f"Sending alarm {alarm_url} с камеры {ip_suffix}")
                self.response_queue.put(('alarm', f"Sending alarm {alarm_url} с камеры {ip_suffix}"))
                async with aiohttp.ClientSession() as session:
                    async with session.get(alarm_url) as response:
                        if response.status == 200:
                            self.logger.info(f"Alarm sent successfully {alarm_url} с камеры {ip_suffix}")
                            self.response_queue.put(
                                ('alarm', f"Alarm sent successfully {alarm_url} с камеры {ip_suffix}"))
                        else:
                            self.logger.error(f"Failed to send alarm {alarm_url}, с камеры {ip_suffix}, "
                                              f"status code: {response.status}")
                            self.response_queue.put(
                                ('alarm',
                                 f"Failed to send alarm {alarm_url}"))
            except Exception as e:
                self.logger.error(f"Error sending alarm {alarm_url}: {e}")
                self.response_queue.put(
                    ('alarm',
                     f"Error sending alarm  {alarm_url}"))

    async def process_alarms(self):
        while self.running.value:
            while not self.alarm_queue.empty():
                command, alarm_url, ip_suffix = self.alarm_queue.get()
                if command == 'alarm':
                    await self.send_alarm(alarm_url, ip_suffix)
            await asyncio.sleep(1)

    def run(self):
        self.initialize_logger()
        self.logger.info("Alarm processor starting")
        try:
            asyncio.run(self.process_alarms())
            self.logger.info("Alarm processor started")
        except Exception as e:
            self.logger.error(f"Error in alarm processor: {e}")
        self.logger.info("Alarm processor stopped")
