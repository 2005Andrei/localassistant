import os
import threading
import time
import requests

class PromptPipeline():
    def __init__(self, request):
        self.current_prompt = []
        self.last_updated_time = None
        self.ready = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        self.thread = threading.Thread(target=self.check_time)
        self.thread.daemon = True
        self.thread.start()

        self.request = request

    def add_data(self, sentence):
        with self._lock: 
            if not self.ready:
                self.current_prompt.append(sentence)
                self.last_updated_time = time.time()
            else:
                self.send_data()
    def send_data(self):
        self.request.send(self.current_prompt)

    def check_time(self):
        while not self._stop_event.is_set():
            with self._lock:
                if self.last_updated_time is not None and (time.time() - self.last_updated_time > 5) and self.current_prompt:
                    self.ready = True
                    self.send_data()
                    self.reset()

                time.sleep(0.2)

    def reset(self):
        self.current_prompt = []
        self.last_updated_time = None
        self.ready = False

    def close(self):
        print("Closing thread in prompt pipeline")
        self._stop_event.set()
        self.thread.join()

import requests
import json

class MidPoint: # between stt and tts
    def __init__(self, tts):
        self.tts = tts
        self.url = "http://localhost:11434/api/generate"
        self.model = "butler-code" # my model I set up - when this repo gets sufficiently good I'll write a comprehnsive readme for any lost soul so that you don't have to know anything prior
    
    def send(self, data):
        if len(data) > 1:
            prompt = '... '.join(data)
        else:
            prompt = data[0]
        
        print("Prompt: ", prompt)

        payload = {
            "model": self.model,
            "prompt": prompt
        }

        
        full_response = []

        with requests.post(self.url, json=payload, stream=True) as response:
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            full_response += data['response']
                        if data.get('done'):
                            break
            else:
                print("Error: ", response.text)
                return

        sentence = ''.join(full_response)
        print("heeey over heere")
        self.tts.say(sentence)

    def close():
        print("idk just closing")
        return True
