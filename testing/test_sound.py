import socket
import json
import hashlib
import struct

# Константы для команд
LOGIN_REQ2 = 1000
TALK_CLAIM = 1434
TALK_REQ = 1430
TALK_CU_PU_DATA = 1432


class SofiaCtl:
    def __init__(self, user, password, host, port, timeout=30):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.socket = None
        self.sid = 0
        self.sequence = 0
        self.timeout = timeout

    def connect(self):
        print(f"Connecting to {self.host}:{self.port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(self.timeout)

    def disconnect(self):
        if self.socket:
            self.socket.close()
            print("Disconnected")

    def make_hash(self, password):
        md5_hash = hashlib.md5(password.encode()).digest()
        hash_result = ''
        for i in range(8):
            n = (md5_hash[2 * i] + md5_hash[2 * i + 1]) % 0x3e
            if n > 9:
                if n > 35:
                    n += 61
                else:
                    n += 55
            else:
                n += 0x30
            hash_result += chr(n)
        return hash_result

    def send_packet(self, msgid, params):
        pkt_prefix_1 = [0xff, 0x00, 0x00, 0x00]
        pkt_type = msgid
        msgid = struct.pack('h', 0) + struct.pack('h', pkt_type)
        pkt_prefix_data = struct.pack('4B', *pkt_prefix_1) + struct.pack('i', self.sid) + struct.pack('i',
                                                                                                      self.sequence) + msgid
        pkt_params_data = ''

        if params is not None:
            pkt_params_data = json.dumps(params)

        pkt_params_data += chr(0x0a)
        pkt_data = pkt_prefix_data + struct.pack('i', len(pkt_params_data)) + pkt_params_data.encode()
        self.sequence += 1
        print(f"Sending packet: {pkt_data}")
        self.socket.send(pkt_data)

    def receive_response(self):
        try:
            print("Receiving response...")
            header = self.socket.recv(24)
            if len(header) != 24:
                raise ValueError("Incomplete header received")
            print(f"Header received: {header}")

            version, sid, seq, channel, endflag, msgid, size = struct.unpack('4s2i2B2i', header)
            reply_head = {
                'Version': version,
                'SessionID': sid,
                'Sequence': seq,
                'MessageId': msgid,
                'Content_Length': size,
                'Channel': channel,
                'EndFlag': endflag
            }
            self.sid = sid

            data = b''
            while len(data) < size:
                packet = self.socket.recv(size - len(data))
                if not packet:
                    raise ValueError("Incomplete data received")
                data += packet

            print(f"Received data: {data}")
            return reply_head, data
        except Exception as e:
            print(f"Error receiving response: {e}")
            raise

    def login(self):
        data = {
            'EncryptType': 'MD5',
            'LoginType': 'DVRIP-Web',
            'PassWord': self.make_hash(self.password),
            'UserName': self.user
        }
        print(f"Login data: {data}")
        self.send_packet(LOGIN_REQ2, data)
        reply_head, data = self.receive_response()
        response = json.loads(data.decode().strip())
        if response['Ret'] >= 200:
            raise Exception('Authentication failed')
        self.sid = response['SessionID']
        return response

    def send_audio(self, input_file):
        # Step 1: Send TALK_CLAIM
        claim_data = {
            'Name': 'OPTalk',
            'OPTalk': {
                'Action': 'Claim',
                'AudioFormat': {
                    'BitRate': 64000,  # проверено и исправлено
                    'EncodeType': 'G711A',  # исправлено на правильное значение
                    'SampleBit': 8,
                    'SampleRate': 8000
                }
            }
        }
        self.send_packet(TALK_CLAIM, claim_data)
        self.receive_response()

        # Step 2: Send TALK_REQ
        talk_data = {
            'Name': 'OPTalk',
            'OPTalk': {
                'Action': 'Start',
                'AudioFormat': {
                    'BitRate': 64000,  # проверено и исправлено
                    'EncodeType': 'G711A',  # исправлено на правильное значение
                    'SampleBit': 8,
                    'SampleRate': 8000
                }
            }
        }
        self.send_packet(TALK_REQ, talk_data)
        self.receive_response()

        # Step 3: Send audio data
        with open(input_file, 'rb') as f:
            while True:
                audio_data = f.read(320)
                if not audio_data:
                    break
                audio_pkt = self.build_audio_packet(audio_data)
                self.socket.send(audio_pkt)
                self.receive_response()

    def build_audio_packet(self, audio_data):
        audio_header = struct.pack('6B', 0x00, 0x00, 0x01, 0xFA, 0x0E, 0x02) + struct.pack('H', len(audio_data))
        return self.build_raw_packet(TALK_CU_PU_DATA, audio_header + audio_data)

    def build_raw_packet(self, msgid, params):
        pkt_prefix_1 = [0xff, 0x00, 0x00, 0x00]
        pkt_type = msgid
        msgid = struct.pack('h', 0) + struct.pack('h', pkt_type)
        pkt_prefix_data = struct.pack('4B', *pkt_prefix_1) + struct.pack('i', self.sid) + struct.pack('i',
                                                                                                      self.sequence) + msgid
        pkt_data = pkt_prefix_data + struct.pack('i', len(params)) + params
        self.sequence += 1
        return pkt_data

    def talk(self, input_file, output_file=None):
        self.connect()
        self.login()
        self.send_audio(input_file)
        self.disconnect()


# Запуск функции
ctl = SofiaCtl('admin', 'Lud2704asz', '192.168.1.41', 34567)
ctl.talk('lay.pcm')
