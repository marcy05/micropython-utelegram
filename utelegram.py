"""
This code will be executed on Raspberry Pi Pico W.
During tests with Firmware micropython-firmware-pico-w-130623.uf2
    it was NOT possible to get a response from the REST request
    using threading.
    Because of this the suggestion is to use it on the main
    thread in which it worked perfectly.
"""


import time
import gc
import urequests


class TelegramMessage:
    def __init__(self, message):
        self._message = message
        self.chat_id = 0
        self.msg_text = ""

        self._get_content()

    def _get_content(self):
        if 'text' in self._message['message']:
            self.chat_id = self._message['message']['chat']['id']
            self.msg_text = self._message['message']['text']


class Ubot:
    def __init__(self, token, offset=0):
        self.url = 'https://api.telegram.org/bot' + token
        self.commands = {}
        self.default_handler = None
        self.message_offset = offset
        self.sleep_btw_updates = 3

    def send(self, chat_id, text):
        data = {'chat_id': chat_id, 'text': text}
        try:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            response = urequests.post(self.url + '/sendMessage', json=data, headers=headers)
            response.close()
            return True
        except Exception:
            return False

    def read_messages(self):
        result = []
        self.query_updates = {
            'offset': self.message_offset + 1,
            'limit': 1,
            'timeout': 30,
            'allowed_updates': ['message']}

        try:
            # print("Getting messages...")
            # print(f"Link: {self.url + '/getUpdates'}")
            update_messages = urequests.post(self.url + '/getUpdates', json=self.query_updates).json()
            print(update_messages)  # Debug printing
            if 'result' in update_messages:
                for item in update_messages['result']:
                    result.append(item)
            return result
        except (ValueError):
            return None
        except (OSError):
            print("OSError: request timed out")
            return None

    def listen(self):
        while True:
            self.read_once()
            time.sleep(self.sleep_btw_updates)
            gc.collect()

    def read_once(self) -> TelegramMessage | None:
        gc.collect()
        messages = self.read_messages()
        if messages:
            if self.message_offset == 0:
                self.message_offset = messages[-1]['update_id']
                return self.message_handler(messages[-1])
            else:
                for message in messages:
                    if message['update_id'] >= self.message_offset:
                        self.message_offset = message['update_id']
                        return self.message_handler(message)

    def register(self, command, handler) -> None:
        self.commands[command] = handler

    def set_default_handler(self, handler) -> None:
        self.default_handler = handler

    def set_sleep_btw_updates(self, sleep_time):
        self.sleep_btw_updates = sleep_time

    def message_handler(self, message) -> str | None:
        if 'text' in message['message']:
            parts = message['message']['text'].split(' ')
            if parts[0] in self.commands:
                return self.commands[parts[0]](message)
            else:
                if self.default_handler:
                    return self.default_handler(message)
