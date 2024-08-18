from logging.handlers import RotatingFileHandler
import telebot
import multiprocessing
import logging
import time
import threading


class TelegramBotProcessor(multiprocessing.Process):
    def __init__(self, telegram_token, chat_id, command_queue, response_queue):
        super().__init__()
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.running = multiprocessing.Value('b', True)
        self.stop_message = False

    def initialize_logger(self):
        self.logger = logging.getLogger('TelegramBotProcessor')
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler('logs/telegram_bot.log', maxBytes=10240, backupCount=10)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def initialize_bot_handlers(self, bot):
        @bot.message_handler(commands=['now'])
        def handle_now(message):
            self.logger.debug("Received 'now' command")
            try:
                ip_suffix = int(message.text.split()[1])
                self.command_queue[ip_suffix].put('request_snapshot')
                bot.send_message(chat_id=self.chat_id,
                                 text=f"Запрос снимка для камеры с IP: {ip_suffix}")
            except (IndexError, ValueError):
                bot.reply_to(message, "Используйте команду в формате: /now <последние цифры IP>")

        @bot.message_handler(commands=['stop'])
        def handle_stop(message):
            self.logger.debug("Received 'stop' command")
            self.stop_message = True
            bot.send_message(chat_id=self.chat_id, text="Остановлена отправка сообщений")

        @bot.message_handler(commands=['start'])
        def handle_start(message):
            self.logger.debug("Received 'start' command")
            self.stop_message = False
            bot.send_message(chat_id=self.chat_id, text="Возобновлена отправка сообщений")

        @bot.message_handler(commands=['exit'])
        def handle_exit(message):
            self.logger.debug("Received 'exit' command")
            self.running.value = False
            bot.send_message(chat_id=self.chat_id, text="Завершение работы")
            bot.stop_polling()

        @bot.message_handler(commands=['start_cam'])
        def handle_start_cam(message):
            ip_suffix = int(message.text.split()[1]) if len(
                message.text.split()) > 1 else None
            if ip_suffix:
                bot.send_message(chat_id=self.chat_id,
                                 text=f"Запрос на запуск камеры с IP: {ip_suffix} получен")
                self.logger.debug(
                    f"Received 'start_cam' command for IP suffix {ip_suffix}")
                command_queue = self.command_queue.get('main', None)
                if command_queue:
                    try:
                        command_queue.put(('start_camera', ip_suffix))
                    except Exception as e:
                        self.logger.error(f"Error request starting  камеры с IP: {ip_suffix}: {e}")
                        bot.send_message(chat_id=self.chat_id,
                                         text=f"Error request starting  камеры с IP: {ip_suffix}: {e}")
                else:
                    try:
                        self.command_queue['main'].put(('start_camera', ip_suffix))
                    except Exception as e:
                        self.logger.error(f"Error request starting  камеры с IP: {ip_suffix}: {e}")
                        bot.send_message(chat_id=self.chat_id,
                                         text=f"Error request starting  камеры с IP: {ip_suffix}: {e}")
            else:
                bot.reply_to(message,
                             "Используйте команду в формате: /start_cam  <последние цифры IP>")

        @bot.message_handler(commands=['stop_cam'])
        def handle_stop_cam(message):
            command_queue = None
            ip_suffix = int(message.text.split()[1]) if len(
                message.text.split()) > 1 else None
            if ip_suffix:
                command_queue = self.command_queue.get(ip_suffix, None)

            if command_queue:
                self.logger.debug(
                    f"Received 'stop_cam' command for IP suffix {ip_suffix}")
                try:
                    command_queue.put('stop_camera')
                    bot.send_message(chat_id=self.chat_id,
                                     text=f"Запрос на остановку камеры с IP: {ip_suffix} получен")
                    # del self.command_queue[ip_suffix]
                except Exception as e:
                    self.logger.error(
                        f"Error request stop for camera IP: {ip_suffix}: {e}")
                    bot.send_message(chat_id=self.chat_id,
                                     text=f"Error request stop for camera IP: {ip_suffix}: {e}")
            else:
                self.logger.error(f'Error in command. Сamera not found {message.text}')
                bot.reply_to(message,
                             "Такой камеры не найдено. Используйте команду в формате: /stop_cam  <последние цифры IP>, только для работающей камеры")

        @bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            self.logger.debug("Received a message")
            bot.reply_to(message, "привет")

    def process_queue(self, bot):
        while self.running.value:
            try:
                if not self.response_queue.empty():
                    response = self.response_queue.get()
                    if isinstance(response, tuple) and len(response) == 2:
                        command, data = response
                        if command == 'notification':
                            if not self.stop_message:
                                image_path, ip_suffix = data
                                with open(image_path, 'rb') as img_file:
                                    bot.send_photo(chat_id=self.chat_id,
                                                   photo=img_file,
                                                   caption=f"Обнаружена кошка на камере {ip_suffix}")
                                    del ip_suffix
                        elif command == 'snapshot_done':
                            image_path = data
                            with open(image_path, 'rb') as img_file:
                                bot.send_photo(chat_id=self.chat_id,
                                               photo=img_file,
                                               caption="Запрошенный snapshot")
                        elif command == 'alarm':
                            if not self.stop_message:
                                bot.send_message(chat_id=self.chat_id,
                                                 text=data)
                        elif command == 'camera_status':
                            bot.send_message(chat_id=self.chat_id,
                                             text=data)
                        # elif command == 'replacing_command_queue':
                        #     print(1, data)
                        #     self.command_queue = data
                        #     print(data)
                    else:
                        self.logger.error(
                            f'Error in command. {response}')
                        bot.send_message(chat_id=self.chat_id,
                                         text='Ошибка в команде')

            except Exception as e:
                self.logger.error(f"Error processing queue: {e}")
            time.sleep(1)

    def clear_telegram_updates(self, bot):
        self.logger.debug("Clearing Telegram updates")
        try:
            updates = bot.get_updates(offset=-1)
            if updates:
                bot.get_updates(offset=updates[-1].update_id + 1,
                                timeout=1)
            self.logger.debug("Cleared Telegram updates")
        except Exception as e:
            self.logger.error(f"Error clearing Telegram updates: {e}")

    def run(self):
        self.initialize_logger()
        bot = telebot.TeleBot(self.telegram_token)
        self.clear_telegram_updates(bot)
        self.initialize_bot_handlers(bot)
        self.logger.debug("Starting TelegramBotProcessor")
        queue_thread = None
        for i in range(5):
            try:
                self.logger.debug(f"started queue_thread")
                queue_thread = threading.Thread(target=self.process_queue,
                                                args=(bot,))
                queue_thread.start()
                break
            except Exception as e:
                self.logger.error(f"Error start queue_thread: {e}")
                time.sleep(5)
                self.logger.debug(f"repeated started queue_thread")
                queue_thread = None
        if not queue_thread:
            self.logger.error("TelegramBotProcessor not working")

        self.logger.debug(f"starting bot polling")
        while self.running.value:
            try:
                bot.polling(none_stop=True, interval=10)
            except Exception as e:
                self.logger.error(f"Error in bot polling: {e}")
                time.sleep(60)
                self.logger.debug(f"repeated started bot.polling")
