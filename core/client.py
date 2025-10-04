import os
import threading
import time


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



class MidPoint: # between stt and tts
    def __init__(self, tts):
        self.tts = tts

    def send(data):
        #process texrt
        # do a curl request
        # get data - and then call tts.say()

        
