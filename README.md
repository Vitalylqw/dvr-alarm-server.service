# Camera and Telegram Bot Processor## Описание проекта

Этот проект предназначен для обработки изображений с камер наблюдения, детекции объектов (кошек) на них и отправки уведомлений через Telegram.
Проект также включает возможность отправки тревожных сигналов по HTTP-запросам и управление камерами через Telegram-бота.

Когда система обнаруживает объект (например, кошку), она отправляет тревожный сигнал на указанный `alarm_url` 
в виде HTTP-запроса. Модели глубокого обучения YOLO v10 обучены на распознавании кошек, чтобы в случае их 
появления отправить сигнал тревоги для отпугивания на отслеживаемой территории.

В проекте используются две модели:
-**Первая модель**: работает быстро и проверяет каждый снимок с камеры в реальном времени (каждую секунду).
-**Вторая модель**: более точная, но медленная. Она используется для подтверждения обнаруженного объекта перед отправкой тревоги.

### Основные компоненты:
1.**CameraProcessor** — отвечает за взаимодействие с ONVIF камерами, захват изображений и их обработку с использованием моделей YOLO.
2.**TelegramBotProcessor** — управляет Telegram-ботом, обрабатывает команды от пользователей и отправляет уведомления при обнаружении объектов на камерах.
3.**AlarmProcessor** — отвечает за отправку тревожных уведомлений через HTTP-запросы.
4.**Main** — основной управляющий скрипт, который запускает все процессы и следит за их работой.

## Установка и настройка  Зависимости

Для работы проекта требуются следующие библиотеки:

-`opencv-python`-`numpy`-`multiprocessing`-`onvif`-`urllib`-`ultralytics`-`telebot`-`aiohttp`-`python-dotenv`

Вы можете установить все зависимости с помощью команды:

```bash
pip install -r requirements.txt

Конфигурация
Перед запуском проекта убедитесь, что у вас настроены следующие переменные окружения:

TELEGRAM_BOT_TOKEN — токен вашего Telegram-бота.
CHAT_ID — ID чата в Telegram, куда будут отправляться уведомления.
CAMERA_IPS — список IP-адресов камер для мониторинга и настройки их параметров.
Создайте файл .env в корневой директории проекта и добавьте в него следующие строки:

TELEGRAM_BOT_TOKEN=ваш_телеграм_бот_токен
CHAT_ID=ваш_чат_id
CAMERA_IPS='[
    {
        "ip": 10,
        "user": "admin",
        "passw": "12345",
        "alarm_url": "http://example.com/alarm",
        "port": 8899,
        "area": [100, 100, 200, 200],
        "track": true
    },
    {
        "ip": 11,
        "user": "admin",
        "passw": "12345",
        "alarm_url": null,
        "port": 8899,
        "area": null,
        "track": true
    }
]'

Настройки камер
Для корректной работы системы необходимо задать параметры каждой камеры в формате JSON в переменной окружения CAMERA_IPS. 
Эти параметры описывают каждую камеру, такие как её IP-адрес, учётные данные, зоны интереса для детекции и настройки
тревожных уведомлений.
Пример конфигурации камеры в .env:
CAMERA_IPS='[
    {
        "ip": 57,
        "user": "admin",
        "passw": "password",
        "alarm_url": "http://192.168.1.93/alarm",
        "port": 8899,
        "area": null,
        "track": true
    },
    {
        "ip": 65,
        "user": "admin",
        "passw": "password",
        "alarm_url": null,
        "port": 8899,
        "area": [100, 150, 400, 300],
        "track": true
    }
]'

Описание каждого элемента конфигурации:
ip (обязательное поле):

Описание: Последний октет IP-адреса камеры в локальной сети. Полный IP-адрес формируется автоматически, добавляя префикс, например, 192.168.1..
Пример: Если ip = 57, полный IP-адрес будет 192.168.1.57.
user (обязательное поле):

Описание: Имя пользователя для доступа к камере.
Пример: admin.
passw (обязательное поле):

Описание: Пароль для доступа к камере.
Пример: password.
alarm_url (опциональное поле):

Описание: URL для отправки тревожного уведомления. Если система обнаруживает что-то в кадре, она отправит запрос по этому адресу.
Пример: http://192.168.1.93/alarm.
Значение по умолчанию: null (если не требуется отправка тревог).
port (обязательное поле):

Описание: Порт, используемый для подключения к камере.
Пример: 8899.
area (опциональное поле):

Описание: Зона интереса (ROI - Region of Interest), ограничивающая область изображения, которая будет анализироваться моделью. Задаётся в виде списка координат [x, y, width, height], где:
x, y — координаты верхнего левого угла области,
width, height — ширина и высота области в пикселях.
Пример: [100, 150, 400, 300] означает, что анализируемая область начинается с точки (100, 150) и имеет размер 400x300 пикселей.
Значение по умолчанию: null (вся область изображения будет анализироваться).
track (обязательное поле):

Описание: Указывает, должна ли система отслеживать камеру. Если значение true, система будет включать детекцию объектов на этой камере.
Пример: true.
Значение по умолчанию: Если отслеживание не требуется, установите false.

Запуск проекта
Запустите основной файл проекта:
python main.py

Структура файлов
camera_processor.py — класс для обработки видео с камер наблюдения, детекция объектов с использованием YOLO и отправка уведомлений о событиях.
telegram_processor.py — класс для обработки команд Telegram-бота и отправки уведомлений в чат.
alarm_processor.py — класс для отправки тревожных сигналов по HTTP-запросам при обнаружении объектов на видео.
main.py — основной файл, который запускает все процессы, взаимодействует с камерами, телеграм-ботом и тревожными сигналами.

Логирование
Все события в системе логируются в папку logs, где для каждого компонента создается отдельный лог-файл. Логирование осуществляется с помощью библиотеки logging с использованием ротации логов для ограничения их объема.

Управление через Telegram
Telegram-бот поддерживает следующие команды:

/now <IP> — запросить текущее изображение с камеры.
/start_cam <IP> — запуск отслеживания камеры с указанным IP.
/stop_cam <IP> — остановка отслеживания камеры.
/start — возобновить отправку сообщений.
/stop — остановить отправку сообщений.
/exit — остановить бота и завершить все процессы.


# Camera and Telegram Bot Processor## Project Description

This project is designed for processing images from surveillance cameras, detecting objects (cats) on them, and sending notifications via Telegram. The project also includes the ability to send alarm signals via HTTP requests and control the cameras through a Telegram bot.

When the system detects an object (e.g., a cat), it sends an alarm signal to the specified `alarm_url` via an HTTP request. The deep learning YOLO v10 models are trained to recognize cats so that, upon detection, the system can trigger alarms to scare them away from the monitored area.

The project uses two models:
-**The first model**: operates quickly and checks each image from the camera in real-time (every second).
-**The second model**: is more accurate but slower. It is used to confirm the detected object before sending an alarm.

### Main Components:
1.**CameraProcessor** — responsible for interacting with ONVIF cameras, capturing images, and processing them using YOLO models.
2.**TelegramBotProcessor** — manages the Telegram bot, processes user commands, and sends notifications when objects are detected on the cameras.
3.**AlarmProcessor** — handles the sending of alarm notifications via HTTP requests.
4.**Main** — the main script that launches all processes and monitors their operation.

## Installation and Setup### Dependencies

The project requires the following libraries to work:

-`opencv-python`-`numpy`-`multiprocessing`-`onvif`-`urllib`-`ultralytics`-`telebot`-`aiohttp`-`python-dotenv`

You can install all dependencies using the following command:

```bash
pip install -r requirements.txt

Configuration
Before running the project, make sure you have set up the following environment variables:

TELEGRAM_BOT_TOKEN — your Telegram bot token.
CHAT_ID — the Telegram chat ID where notifications will be sent.
CAMERA_IPS — a list of IP addresses for cameras to monitor and their configuration parameters.
Create a .env file in the root directory of the project and add the following lines:
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_chat_id
CAMERA_IPS='[
    {
        "ip": 10,
        "user": "admin",
        "passw": "12345",
        "alarm_url": "http://example.com/alarm",
        "port": 8899,
        "area": [100, 100, 200, 200],
        "track": true
    },
    {
        "ip": 11,
        "user": "admin",
        "passw": "12345",
        "alarm_url": null,
        "port": 8899,
        "area": null,
        "track": true
    }
]'
Camera Configuration
To ensure the system works correctly, you need to configure each camera in JSON format in the CAMERA_IPS environment variable. These parameters describe each camera, such as its IP address, credentials, region of interest for detection, and alarm notification settings.

Example camera configuration in .env:
CAMERA_IPS='[
    {
        "ip": 57,
        "user": "admin",
        "passw": "password",
        "alarm_url": "http://192.168.1.93/alarm",
        "port": 8899,
        "area": null,
        "track": true
    },
    {
        "ip": 65,
        "user": "admin",
        "passw": "password",
        "alarm_url": null,
        "port": 8899,
        "area": [100, 150, 400, 300],
        "track": true
    }
]'
Description of each configuration element:
ip (required field):

Description: The last octet of the camera's IP address in the local network. The full IP address is automatically formed by adding a prefix, such as 192.168.1..
Example: If ip = 57, the full IP address will be 192.168.1.57.
user (required field):

Description: The username to access the camera.
Example: admin.
passw (required field):

Description: The password to access the camera.
Example: password.
alarm_url (optional field):

Description: The URL for sending alarm notifications. If the system detects something in the frame, it will send a request to this address.
Example: http://192.168.1.93/alarm.
Default Value: null (if alarm sending is not required).
port (required field):

Description: The port used to connect to the camera.
Example: 8899.
area (optional field):

Description: The region of interest (ROI) that limits the area of the image to be analyzed by the model. It is specified as a list of coordinates [x, y, width, height], where:
x, y — the coordinates of the top-left corner of the area,
width, height — the width and height of the area in pixels.
Example: [100, 150, 400, 300] means that the analyzed area starts at point (100, 150) and has a size of 400x300 pixels.
Default Value: null (the entire image will be analyzed).
track (required field):

Description: Specifies whether the system should track this camera. If set to true, the system will enable object detection on this camera.
Example: true.
Default Value: Set to false if tracking is not required.
Running the Project
Run the main project file:
python main.py

File Structure
camera_processor.py — the class responsible for processing video from surveillance cameras, detecting objects using YOLO, and sending event notifications.
telegram_processor.py — the class for processing Telegram bot commands and sending notifications to the chat.
alarm_processor.py — the class responsible for sending alarm signals via HTTP requests when objects are detected in the video.
main.py — the main file that launches all processes, interacts with cameras, the Telegram bot, and alarm signals.
Logging
All system events are logged in the logs folder, where a separate log file is created for each component. Logging is handled using the logging library with log rotation to limit the file size.

Telegram Control
The Telegram bot supports the following commands:

/now <IP> — request the current image from the camera.
/start_cam <IP> — start monitoring the camera with the specified IP.
/stop_cam <IP> — stop monitoring the camera.
/start — resume sending messages.
/stop — stop sending messages.
/exit — stop the bot and terminate all processes.





