import os
import time
from queue import Queue

import numpy as np
from silero_vad import VADIterator, load_silero_vad
from sounddevice import InputStream
from faster_whisper import WhisperModel


class FasterWhisperTranscriber:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        print(f"Loading '{model_size}'...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.sampling_rate = 16000
        

        self.__call__(np.zeros(int(self.sampling_rate * 0.5), dtype=np.float32))
        print("Model should be loaded and ready")
        
    def __call__(self, audio_data):
        if len(audio_data) / self.sampling_rate < 0.2:
            return ""
            
        audio_float32 = audio_data.astype(np.float32)
        
        try:
            segments, _ = self.model.transcribe(
                audio_float32,
                beam_size=3,
                best_of=3,
                temperature=0.0,
                compression_ratio_threshold=2.0,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.7,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300)
            )
            
            text = " ".join([segment.text.strip() for segment in segments]).strip()
            return text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""


class TranscriptionFileManager:
    def __init__(self, output_dir="./.bin"):
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.file_path = os.path.join(output_dir, f"transcription_{timestamp}.txt")
        
        self.file = open(self.file_path, 'w+', encoding='utf-8')
        print(f"[+] Transcriptions saved to: {self.file_path}")
        
    def write_transcription(self, text, is_partial=False):
        if not text.strip():
            return
            
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        prefix = "[PARTIAL] " if is_partial else "[FINAL]   "
        line = f"{prefix}[{timestamp}] {text}\n"
        
        self.file.write(line)
        self.file.flush()
        
    def get_full_transcription(self):
        self.file.seek(0)
        return self.file.read()
        
    def close(self):
        if not self.file.closed:
            self.file.close()
            
    def __del__(self):
        self.close()


def create_input_callback(q):
    def input_callback(data, frames, time, status):
        if status:
            print(status)
        q.put((data.copy().flatten(), status))
    return input_callback


def print_captions(text, caption_cache, file_manager=None, is_partial=False, max_line_length=80):
    text = text.strip()
    if not text:
        return
        
    text = ' '.join(text.split())
    
    if len(text) < max_line_length:
        for caption in caption_cache[-2:]:
            combined = caption + " " + text
            if len(combined) > max_line_length:
                break
            text = combined
            
    if len(text) > max_line_length:
        text = text[-max_line_length:]
    else:
        text = " " * (max_line_length - len(text)) + text
        
    
    if file_manager and text.strip() and not is_partial:
        file_manager.write_transcription(text.strip(), is_partial=False)


class EnhancedVADHandler:
    def __init__(self, vad_iterator, sampling_rate, pre_speech_buffer_ms=300):
        self.vad = vad_iterator
        self.sampling_rate = sampling_rate
        self.speech_buffer = np.empty(0, dtype=np.float32)
        self.pre_speech_buffer = np.empty(0, dtype=np.float32)
        self.max_pre_speech_samples = int(pre_speech_buffer_ms * sampling_rate / 1000)
        self.is_speaking = False
        
    def process_chunk(self, chunk):
        self.pre_speech_buffer = np.concatenate([self.pre_speech_buffer, chunk])
        if len(self.pre_speech_buffer) > self.max_pre_speech_samples:
            self.pre_speech_buffer = self.pre_speech_buffer[-self.max_pre_speech_samples:]
            
        speech_dict = self.vad(chunk)
        
        if speech_dict and "start" in speech_dict and not self.is_speaking:
            self.is_speaking = True
            self.speech_buffer = np.concatenate([self.pre_speech_buffer, chunk])
            self.pre_speech_buffer = np.empty(0, dtype=np.float32)
            return {"start": True}
            
        elif speech_dict and "end" in speech_dict and self.is_speaking:
            self.is_speaking = False
            result_buffer = self.speech_buffer.copy()
            self.speech_buffer = np.empty(0, dtype=np.float32)
            return {"end": True, "speech": result_buffer}
            
        elif self.is_speaking:
            self.speech_buffer = np.concatenate([self.speech_buffer, chunk])
            
        return None


def soft_reset(vad_iterator):
    vad_iterator.reset_states()


def run(
    model_size="base",
    device="cpu", 
    compute_type="int8",
    sampling_rate=16000,
    chunk_size=512,
    lookback_chunks=8,
    max_line_length=80,
    max_speech_secs=20,
    min_refresh_secs=1.0,
    vad_threshold=0.6,
    min_silence_duration_ms=300,
    pre_speech_buffer_ms=300,
    output_dir="./bin"
):
    
    transcriber = FasterWhisperTranscriber(model_size, device, compute_type)
    file_manager = TranscriptionFileManager(output_dir)

    vad_model = load_silero_vad(onnx=True)
    vad_iterator = VADIterator(
        model=vad_model, 
        sampling_rate=sampling_rate, 
        threshold=vad_threshold, 
        min_silence_duration_ms=min_silence_duration_ms
    )
    
    vad_handler = EnhancedVADHandler(vad_iterator, sampling_rate, pre_speech_buffer_ms)

    q = Queue()
    stream = InputStream(
        samplerate=sampling_rate, 
        channels=1, 
        blocksize=chunk_size, 
        dtype=np.float32, 
        callback=create_input_callback(q)
    )

    stream.start()

    caption_cache = []
    lookback_size = lookback_chunks * chunk_size
    speech_buffer = np.empty(0, dtype=np.float32)

    recording = False
    last_partial_time = 0
    consecutive_empty = 0

    def finalize_transcription(audio_data):
        if len(audio_data) / sampling_rate < 0.3:
            return np.empty(0, dtype=np.float32)
            
        text = transcriber(audio_data)
        
        if text.strip():
            print_captions(text, caption_cache, file_manager, is_partial=False, max_line_length=max_line_length)
            caption_cache.append(text)
        else:
            
        return np.empty(0, dtype=np.float32)

    with stream:
        print_captions("[+] Converse rn!", caption_cache, file_manager, is_partial=False, max_line_length=max_line_length)
        try:
            while True:
                chunk, status = q.get()
                if status:

                speech_buffer = np.concatenate((speech_buffer, chunk))
                if not recording:
                    speech_buffer = speech_buffer[-lookback_size:]

                result = vad_handler.process_chunk(chunk)
                
                if result and "start" in result and not recording:
                    recording = True
                    last_partial_time = time.time()

                elif result and "end" in result and recording:
                    recording = False
                    speech_buffer = finalize_transcription(result["speech"])

                elif recording:
                    current_duration = len(speech_buffer) / sampling_rate
                    if current_duration > max_speech_secs:
                        recording = False
                        
                        speech_buffer = finalize_transcription(speech_buffer)
                        soft_reset(vad_iterator)

                    current_time = time.time()
                    if (current_time - last_partial_time) > min_refresh_secs:
                        partial_text = transcriber(speech_buffer)
                        if partial_text.strip():
                            print_captions(partial_text, caption_cache, None, is_partial=True, max_line_length=max_line_length)
                            consecutive_empty = 0
                        else:
                            consecutive_empty += 1
                            
                        if consecutive_empty > 2:
                            recording = False
                            speech_buffer = np.empty(0, dtype=np.float32)
                            soft_reset(vad_iterator)
                            
                        last_partial_time = current_time
                    
        except KeyboardInterrupt:
            print("\n\n[-] Stopping...")
            stream.close()

            if recording:
                while not q.empty():
                    chunk, _ = q.get()
                    speech_buffer = np.concatenate((speech_buffer, chunk))
                finalize_transcription(speech_buffer)
                
            
            file_manager.close()
