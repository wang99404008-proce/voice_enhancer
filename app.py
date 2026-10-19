import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from pedalboard.io import AudioFile
from pedalboard import (
    Pedalboard,
    HighpassFilter,
    PeakFilter,
    HighShelfFilter,
    Compressor,
    Gain,
    Limiter
)

def get_resource_path(relative_path: str) -> str:
    """相容開發環境與 PyInstaller 打包後的解壓路徑"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class AudioClarifierEngine:
    @staticmethod
    def enhance_clarity(input_path: str, output_path: str, clarity_boost: float, noise_clean: bool, callback=None):
        """
        音訊清晰優化管線：
        - 支援 MP4, MOV, MKV, MP3, WAV, FLAC, M4A 等影音格式輸入
        - 廣播級人聲 EQ (去悶、增強齒音咬字與空氣感)
        - 雙段動態控制與 -1.0 dBFS 極限防爆音
        """
        if callback:
            callback(15, "正在解碼並載入影音檔聲音軌...")

        # 1. 讀取音訊 (Pedalboard 原生支援讀取 MP4/MOV 中的音訊軌)
        with AudioFile(input_path) as f:
            audio = f.read(f.frames)
            sr = f.samplerate

        if callback:
            callback(35, "正在濾除超低頻底噪與雜音...")

        # 2. 建構清晰化效果鏈 (莫蘭迪調音：透亮、清晰、不刺耳、不爆音)
        effects = []

        # (1) 去除超低頻嗡鳴與空調聲 (85Hz 以下)
        effects.append(HighpassFilter(cutoff_frequency_hz=85.0))

        # (2) 消除 280Hz 附近的發悶箱體共振
        effects.append(PeakFilter(cutoff_frequency_hz=280.0, gain_db=-2.5, q=1.0))

        # (3) 增強人聲咬字與清晰度頻段 (3.2 kHz)
        clarity_gain = clarity_boost * 4.5  # 依照使用者設定調節
        effects.append(PeakFilter(cutoff_frequency_hz=3200.0, gain_db=clarity_gain, q=1.2))

        # (4) 提升高頻空氣感與通透度 (8.5 kHz 以上)
        air_gain = clarity_boost * 3.0
        effects.append(HighShelfFilter(cutoff_frequency_hz=8500.0, gain_db=air_gain))

        if callback:
            callback(60, "正在套用動態壓縮平衡音量...")

        # (5) 智慧壓縮：拉平說話忽大忽小的聲音
        effects.append(Compressor(
            threshold_db=-18.0,
            ratio=2.8,
            attack_ms=15.0,
            release_ms=80.0
        ))

        # (6) 總音量整體平滑增益補償
        effects.append(Gain(gain_db=2.5))

        # (7) 廣播級極限器 (Limiter)：牢牢鎖在 -1.0 dBFS，保證絕對不破音！
        effects.append(Limiter(threshold_db=-1.0, release_ms=50.0))

        board = Pedalboard(effects)

        if callback:
            callback(80, "正在計算聲音渲染...")

        processed_audio = board(audio, sr)

        if callback:
            callback(95, "正在匯出高保真音訊...")

        # 3. 輸出儲存為標準無損 WAV (保留最佳音質)
        with AudioFile(output_path, 'w', sr, processed_audio.shape[0]) as out_f:
            out_f.write(processed_audio)

        if callback:
            callback(100, "優化完成！")

class MorandiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AuraVoice - 離線聲音清晰優化")
        self.geometry("600x480")
        self.resizable(False, False)

        # 莫蘭迪色彩系統 (Morandi Color Palette)
        self.C_BG = "#E8EBE8"          # 莫蘭迪淺灰底色
        self.C_CARD = "#F5F6F4"        # 卡片米灰白
        self.C_PRIMARY = "#758A7A"     # 莫蘭迪灰綠色 (Sage Green)
        self.C_PRIMARY_HOVER = "#627566"
        self.C_SECONDARY = "#8E9DA6"   # 莫蘭迪霧藍灰 (Slate Blue)
        self.C_TEXT = "#3D4540"        # 深石灰文字
        self.C_MUTED = "#7A827D"       # 次要灰色文字
        self.C_BORDER = "#D6DBD5"      # 柔和邊框線條

        self.configure(bg=self.C_BG)

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.clarity_level = tk.DoubleVar(value=1.0)  # 清晰度強化倍率 (0.5 ~ 2.0)

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        # 全域配置
        style.configure(".", background=self.C_BG, foreground=self.C_TEXT, font=("Segoe UI", 9))

        # 卡片 LabelFrame
        style.configure("Morandi.TLabelframe", background=self.C_CARD, bordercolor=self.C_BORDER, relief="solid", borderwidth=1)
        style.configure("Morandi.TLabelframe.Label", background=self.C_CARD, foreground=self.C_TEXT, font=("Segoe UI", 10, "bold"))

        # 輸入框
        style.configure("Morandi.TEntry", fieldbackground="#FFFFFF", foreground=self.C_TEXT, bordercolor=self.C_BORDER)

        # 輔助按鈕
        style.configure("Secondary.TButton", background=self.C_SECONDARY, foreground="#FFFFFF", borderwidth=0, font=("Segoe UI", 9))
        style.map("Secondary.TButton", background=[('active', '#7A8992')])

        # 主執行按鈕
        style.configure("Primary.TButton", background=self.C_PRIMARY, foreground="#FFFFFF", borderwidth=0, font=("Segoe UI", 11, "bold"))
        style.map("Primary.TButton", background=[('active', self.C_PRIMARY_HOVER)])

        # 進度條
        style.configure("Morandi.Horizontal.TProgressbar", troughcolor=self.C_BORDER, background=self.C_PRIMARY, bordercolor=self.C_BG, lightcolor=self.C_PRIMARY, darkcolor=self.C_PRIMARY)

    def build_ui(self):
        root_container = tk.Frame(self, bg=self.C_BG, padx=24, pady=20)
        root_container.pack(fill=tk.BOTH, expand=True)

        # 頂部標題列
        header_frame = tk.Frame(root_container, bg=self.C_BG)
        header_frame.pack(fill=tk.X, pady=(0, 16))

        title_lbl = tk.Label(header_frame, text="AuraVoice 聲音清晰優化", font=("Segoe UI", 16, "bold"), fg=self.C_TEXT, bg=self.C_BG)
        title_lbl.pack(anchor=tk.W)

        subtitle_lbl = tk.Label(header_frame, text="支援 MP4/MOV/MP3/WAV，純離線人聲清晰增強與抗破音處理", font=("Segoe UI", 9), fg=self.C_MUTED, bg=self.C_BG)
        subtitle_lbl.pack(anchor=tk.W, pady=(2, 0))

        # 檔案選取區塊 (卡片樣式)
        file_box = ttk.LabelFrame(root_container, text=" 來源檔案與儲存路徑 ", style="Morandi.TLabelframe", padding="14")
        file_box.pack(fill=tk.X, pady=(0, 14))

        # 輸入行
        lbl_in = tk.Label(file_box, text="影音來源:", fg=self.C_TEXT, bg=self.C_CARD, font=("Segoe UI", 9, "bold"))
        lbl_in.grid(row=0, column=0, sticky=tk.W, pady=6)
        entry_in = ttk.Entry(file_box, textvariable=self.input_file, width=46, style="Morandi.TEntry")
        entry_in.grid(row=0, column=1, padx=8, pady=6)
        btn_in = ttk.Button(file_box, text="瀏覽檔案", style="Secondary.TButton", command=self.select_input)
        btn_in.grid(row=0, column=2, pady=6)

        # 輸出儲存行
        lbl_out = tk.Label(file_box, text="清晰輸出:", fg=self.C_TEXT, bg=self.C_CARD, font=("Segoe UI", 9, "bold"))
        lbl_out.grid(row=1, column=0, sticky=tk.W, pady=6)
        entry_out = ttk.Entry(file_box, textvariable=self.output_file, width=46, style="Morandi.TEntry")
        entry_out.grid(row=1, column=1, padx=8, pady=6)
        btn_out = ttk.Button(file_box, text="變更路徑", style="Secondary.TButton", command=self.select_output)
        btn_out.grid(row=1, column=2, pady=6)

        # 參數微調區塊
        param_box = ttk.LabelFrame(root_container, text=" 清晰度與防破音調節 ", style="Morandi.TLabelframe", padding="14")
        param_box.pack(fill=tk.X, pady=(0, 16))

        lbl_clarity = tk.Label(param_box, text="清晰度增強:", fg=self.C_TEXT, bg=self.C_CARD)
        lbl_clarity.grid(row=0, column=0, sticky=tk.W)
        scale_clarity = ttk.Scale(param_box, from_=0.5, to=2.0, variable=self.clarity_level, orient=tk.HORIZONTAL)
        scale_clarity.grid(row=0, column=1, sticky=tk.EW, padx=12, pady=8)
        param_box.columnconfigure(1, weight=1)

        clarity_hint = tk.Label(param_box, text="極致通透 (內建 -1dB 防爆音)", fg=self.C_MUTED, bg=self.C_CARD, font=("Segoe UI", 8))
        clarity_hint.grid(row=0, column=2, sticky=tk.E)

        # 進度提示
        self.status_label = tk.Label(root_container, text="就緒 (請先匯入影音檔案)", font=("Segoe UI", 9), fg=self.C_MUTED, bg=self.C_BG)
        self.status_label.pack(anchor=tk.W, pady=(0, 6))

        self.progress_bar = ttk.Progressbar(root_container, style="Morandi.Horizontal.TProgressbar", orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 18))

        # 核心啟動按鈕
        self.run_btn = ttk.Button(root_container, text="開始一鍵清晰優化", style="Primary.TButton", command=self.start_processing)
        self.run_btn.pack(fill=tk.X, ipady=6)

    def select_input(self):
        f = filedialog.askopenfilename(
            title="選擇影片或音訊檔案",
            filetypes=[
                ("所有支援影音", "*.mp4 *.mov *.mkv *.avi *.mp3 *.wav *.flac *.m4a *.ogg *.aac"),
                ("影片檔案", "*.mp4 *.mov *.mkv *.avi"),
                ("音訊檔案", "*.mp3 *.wav *.flac *.m4a *.ogg *.aac"),
                ("所有檔案", "*.*")
            ]
        )
        if f:
            self.input_file.set(f)
            base, _ = os.path.splitext(f)
            # 預設匯出高保真 WAV 音訊，確保最頂尖不失真音質
            self.output_file.set(f"{base}_clarified.wav")
            self.status_label.config(text=f"已載入：{os.path.basename(f)}")

    def select_output(self):
        f = filedialog.asksaveasfilename(
            title="選擇輸出路徑",
            defaultextension=".wav",
            filetypes=[("高保真 WAV", "*.wav"), ("FLAC 無損", "*.flac")]
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
            messagebox.showwarning("提示", "請先選擇有效的影片或音訊檔案！")
            return
        if not dst:
            messagebox.showwarning("提示", "請指定輸出檔案儲存路徑！")
            return

        self.run_btn.config(state=tk.DISABLED)

        def worker():
            try:
                AudioClarifierEngine.enhance_clarity(
                    src,
                    dst,
                    clarity_boost=self.clarity_level.get(),
                    noise_clean=True,
                    callback=self.update_progress
                )
                messagebox.showinfo("完成", f"聲音優化成功！\n已儲存清晰音軌至：\n{dst}")
            except Exception as e:
                messagebox.showerror("錯誤", f"處理失敗：\n{str(e)}")
            finally:
                self.run_btn.config(state=tk.NORMAL)
                self.status_label.config(text="就緒")
                self.progress_bar['value'] = 0

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = MorandiApp()
    app.mainloop()
