import threading
import os
from RealtimeSTT import AudioToTextRecorder
import pyaudio

class STT:
    def __init__(self, pipeline):
        self.stop_event = threading.Event()
        self.recorder = None
        self.audio = None
        self.stream = None

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.RATE = 16000
        self.CHANNELS = 1

        self.pipeline = pipeline

    def init_audio(self):
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        self.recorder = AudioToTextRecorder(use_microphone=False, spinner=False)
        print("Converse: ")

    def feed_audio(self):
        try:
            while not self.stop_event.is_set():
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.recorder.feed_audio(data)
        except Exception as e:
            print(f"Exception at audio feed: {e}")
        finally:
            print("Audio stream closed")

    def proc_transcription(self, sentence):
        
        self.pipeline.add_data(sentence)

        if "stop recording" in sentence.lower():
            print("Stop command detected")
            self.stop_event.set()

    def transcribe_audio(self):
        try:
            while not self.stop_event.is_set():
                self.recorder.text(self.proc_transcription)
        except Exception as e:
            print(f"Exception at transcribing: {e}")
        finally:
            pass

    def cleanup(self):
        self.stop_event.set()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
        if self.recorder:
            self.recorder.shutdown()
        if self.pipeline:
            self.pipeline.close()
        print("cleanup done")

    def run(self):
        print("\n\n[+] Initializing transcriber...\n")

        try:
            self.init_audio()

            audio_thread = threading.Thread(target=self.feed_audio)
            transcription_thread = threading.Thread(target=self.transcribe_audio)

            audio_thread.daemon = True
            transcription_thread.daemon = True

            audio_thread.start()
            transcription_thread.start()

            try:
                while not self.stop_event.is_set():
                    self.stop_event.wait(0.1)
            except KeyboardInterrupt:
                print("\nStop initiated by user")
                self.stop_event.set()

        except Exception as e:
            print(f"Error in run method: {e}")
        finally:
            self.cleanup()


class TSS:
    def __init__(self):
        

#if __name__ == "__main__":
#    stt = STT()
#    stt.run()
