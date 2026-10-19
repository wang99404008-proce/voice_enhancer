import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt
from pedalboard import Pedalboard, Compressor, Gain, Limiter

def get_resource_path(relative_path: str) -> str:
    """獲取資源檔案絕對路徑，相容開發環境與 PyInstaller 打包環境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class AudioEnhancerEngine:
    @staticmethod
    def highpass_filter(data: np.ndarray, sr: int, cutoff: float = 80.0) -> np.ndarray:
        """濾除 80Hz 以下震動與低頻底噪"""
        sos = butter(4, cutoff, btype='highpass', fs=sr, output='sos')
        if data.ndim == 1:
            return sosfilt(sos, data)
        return np.vstack([sosfilt(sos, data[ch]) for ch in range(data.shape[0])])

    @staticmethod
    def spectral_denoise(data: np.ndarray, sr: int, strength: float = 0.6) -> np.ndarray:
        """純本地頻譜自適應降噪 (無需聯網)"""
        if strength <= 0.0:
            return data

        # 取單聲道計算雜訊底限
        ref_channel = data[0] if data.ndim > 1 else data
        frame_len = int(sr * 0.02)  # 20ms
        hop_len = frame_len // 2

        # 估算起始 150ms 作為環境背景噪音參照
        noise_samples = ref_channel[: int(sr * 0.15)]
        if len(noise_samples) < frame_len:
            noise_samples = ref_channel

        noise_fft = np.abs(np.fft.rfft(noise_samples[:frame_len]))
        noise_thresh = np.mean(noise_fft) * (1.0 + strength * 2.0)

        def process_channel(ch):
            pad_len = hop_len - (len(ch) % hop_len)
            padded = np.pad(ch, (0, pad_len), mode='constant')
            out = np.zeros_like(padded)
            window = np.hanning(frame_len)

            for i in range(0, len(padded) - frame_len, hop_len):
                frame = padded[i : i + frame_len] * window
                spec = np.fft.rfft(frame)
                mag = np.abs(spec)
                phase = np.angle(spec)

                # 譜減抑制
                gain = np.clip(1.0 - (noise_thresh * strength / (mag + 1e-8)), 0.15, 1.0)
                clean_spec = mag * gain * np.exp(1j * phase)
                out[i : i + frame_len] += np.fft.irfft(clean_spec) * window

            return out[: len(ch)]

        if data.ndim == 1:
            return process_channel(data)
        return np.vstack([process_channel(data[ch]) for ch in range(data.shape[0])])

    @classmethod
    def enhance_file(cls, input_path: str, output_path: str, denoise_strength: float, boost_db: float, callback=None):
        """執行完整音訊優化管線"""
        data, sr = sf.read(input_path, dtype='float32')
        # 轉換成 (channels, samples)
        if data.ndim > 1:
            data = data.T

        if callback:
            callback(25, "正在濾除超低頻噪音...")
        data = cls.highpass_filter(data, sr)

        if callback:
            callback(50, "正在執行離線降噪處理...")
        data = cls.spectral_denoise(data, sr, strength=denoise_strength)

        if callback:
            callback(75, "正在優化動態範圍與標準化音量...")
        # Pedalboard 處理 (Compressor + Limiter)
        board = Pedalboard([
            Compressor(threshold_db=-18.0, ratio=2.5, attack_ms=10.0, release_ms=100.0),
            Gain(gain_db=boost_db),
            Limiter(threshold_db=-0.8)
        ])

        if data.ndim == 1:
            processed = board(data, sr)
        else:
            processed = board(data, sr)

        if callback:
            callback(90, "正在儲存輸出檔案...")

        # 轉回 (samples, channels) 格式寫入
        out_to_save = processed.T if processed.ndim > 1 else processed
        sf.write(output_path, out_to_save, sr)

        if callback:
            callback(100, "處理完成！")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Voice Enhancer 離線聲音優化工具")
        self.geometry("540x440")
        self.resizable(False, False)

        # 設定圖示（若存在）
        ico_path = get_resource_path("icon.ico")
        if os.path.exists(ico_path):
            self.iconbitmap(ico_path)

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.denoise_level = tk.DoubleVar(value=0.6)
        self.gain_level = tk.DoubleVar(value=3.0)

        self.build_ui()

    def build_ui(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        main_frame = ttk.Frame(self, padding="16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 檔案選取區域
        file_box = ttk.LabelFrame(main_frame, text=" 音訊檔案選擇 ", padding="10")
        file_box.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(file_box, text="輸入檔案:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(file_box, textvariable=self.input_file, width=42).grid(row=0, column=1, padx=6)
        ttk.Button(file_box, text="瀏覽...", command=self.select_input).grid(row=0, column=2)

        ttk.Label(file_box, text="輸出儲存:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(file_box, textvariable=self.output_file, width=42).grid(row=1, column=1, padx=6)
        ttk.Button(file_box, text="選擇...", command=self.select_output).grid(row=1, column=2)

        # 參數微調區域
        param_box = ttk.LabelFrame(main_frame, text=" 聲音優化參數 ", padding="10")
        param_box.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(param_box, text="降噪強度:").grid(row=0, column=0, sticky=tk.W, pady=6)
        denoise_scale = ttk.Scale(param_box, from_=0.0, to=1.0, variable=self.denoise_level, orient=tk.HORIZONTAL)
        denoise_scale.grid(row=0, column=1, sticky=tk.EW, padx=8)
        ttk.Label(param_box, text="強").grid(row=0, column=2)

        ttk.Label(param_box, text="人聲音量增益 (dB):").grid(row=1, column=0, sticky=tk.W, pady=6)
        gain_scale = ttk.Scale(param_box, from_=-6.0, to=12.0, variable=self.gain_level, orient=tk.HORIZONTAL)
        gain_scale.grid(row=1, column=1, sticky=tk.EW, padx=8)
        ttk.Label(param_box, text="+12dB").grid(row=1, column=2)
        param_box.columnconfigure(1, weight=1)

        # 進度區域
        self.status_label = ttk.Label(main_frame, text="等待作業開始...", font=("Segoe UI", 9))
        self.status_label.pack(anchor=tk.W, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 16))

        # 執行按鈕
        self.run_btn = ttk.Button(main_frame, text="開始離線優化", command=self.start_processing)
        self.run_btn.pack(ipady=4, fill=tk.X)

    def select_input(self):
        f = filedialog.askopenfilename(
            title="選擇要優化的音訊",
            filetypes=[("音訊檔案", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("所有檔案", "*.*")]
        )
        if f:
            self.input_file.set(f)
            base, ext = os.path.splitext(f)
            self.output_file.set(f"{base}_enhanced.wav")

    def select_output(self):
        f = filedialog.asksaveasfilename(
            title="選擇儲存路徑",
            defaultextension=".wav",
            filetypes=[("WAV 音訊", "*.wav"), ("FLAC 音訊", "*.flac")]
        )
        if f:
            self.output_file.set(f)

    def update_progress(self, percent: int, msg: str):
        self.progress_bar['value'] = percent
        self.status_label.config(text=msg)
        self.update_idletasks()

    def start_processing(self):
        src = self.input_file.get()
        dst = self.output_file.get()

        if not src or not os.path.exists(src):
            messagebox.showwarning("提示", "請先選擇有效的輸入音訊檔案！")
            return
        if not dst:
            messagebox.showwarning("提示", "請指定輸出檔案儲存路徑！")
            return

        self.run_btn.config(state=tk.DISABLED)

        def worker():
            try:
                AudioEnhancerEngine.enhance_file(
                    src,
                    dst,
                    denoise_strength=self.denoise_level.get(),
                    boost_db=self.gain_level.get(),
                    callback=self.update_progress
                )
                messagebox.showinfo("完成", f"音訊優化成功！\n已儲存至：\n{dst}")
            except Exception as e:
                messagebox.showerror("錯誤", f"處理過程中發生錯誤：\n{str(e)}")
            finally:
                self.run_btn.config(state=tk.NORMAL)
                self.status_label.config(text="就緒")
                self.progress_bar['value'] = 0

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
