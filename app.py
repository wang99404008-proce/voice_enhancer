import os
import sys
import ctypes
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pedalboard.io import AudioFile
from pedalboard import (
    Pedalboard,
    HighpassFilter,
    LowpassFilter,
    PeakFilter,
    NoiseGate,
    Compressor,
    Gain,
    Limiter
)

# ----------------- 解決 Windows 介面模糊 (High DPI 銳利化) -----------------
def enable_high_dpi():
    if sys.platform.startswith('win'):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

enable_high_dpi()
# ----------------------------------------------------------------------------

def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class DistinctASREngine:
    """專為語音辨識/判讀特化的聲音清晰化引擎"""
    PRESETS = {
        "conference": {
            "name": "室內會議／演講（消除回音空洞感、大幅清濁提亮）",
            "hp_cutoff": 120.0,
            "lp_cutoff": 7500.0,
            "gate_thresh": -38.0,
            "mud_freq": 320.0,
            "mud_gain": -6.0,
            "presence_freq": 3200.0,
            "presence_gain": 6.5,
            "comp_thresh": -20.0,
            "comp_ratio": 4.5,
            "makeup_gain": 4.0
        },
        "noisy": {
            "name": "吵雜戶外／強噪（激進除噪、切除低頻風噪、人聲極致前推）",
            "hp_cutoff": 160.0,
            "lp_cutoff": 7000.0,
            "gate_thresh": -32.0,
            "mud_freq": 380.0,
            "mud_gain": -8.0,
            "presence_freq": 2800.0,
            "presence_gain": 8.0,
            "comp_thresh": -24.0,
            "comp_ratio": 6.0,
            "makeup_gain": 5.5
        },
        "distant": {
            "name": "微弱耳語／遠距離（小聲自動放大、全面拉平動態音量）",
            "hp_cutoff": 100.0,
            "lp_cutoff": 8000.0,
            "gate_thresh": -46.0,
            "mud_freq": 280.0,
            "mud_gain": -4.0,
            "presence_freq": 3400.0,
            "presence_gain": 7.0,
            "comp_thresh": -28.0,
            "comp_ratio": 6.5,
            "makeup_gain": 7.0
        },
        "interview": {
            "name": "清晰訪談／標準廣播（消除底噪、廣播主播級飽滿通透）",
            "hp_cutoff": 90.0,
            "lp_cutoff": 8200.0,
            "gate_thresh": -42.0,
            "mud_freq": 260.0,
            "mud_gain": -5.0,
            "presence_freq": 3500.0,
            "presence_gain": 5.5,
            "comp_thresh": -18.0,
            "comp_ratio": 3.8,
            "makeup_gain": 3.5
        }
    }

    @classmethod
    def process_file(cls, input_path: str, output_path: str, preset_key: str, callback=None):
        cfg = cls.PRESETS.get(preset_key, cls.PRESETS["conference"])

        if callback:
            callback(15, "正在解碼並分析多媒體音軌...")

        with AudioFile(input_path) as f:
            audio = f.read(f.frames)
            sr = f.samplerate

        if callback:
            callback(35, f"套用【{cfg['name']}】強效人聲提純...")

        chain = [
            HighpassFilter(cutoff_frequency_hz=cfg["hp_cutoff"]),
            NoiseGate(
                threshold_db=cfg["gate_thresh"],
                ratio=10.0,
                attack_ms=5.0,
                release_ms=80.0
            ),
            PeakFilter(cutoff_frequency_hz=cfg["mud_freq"], gain_db=cfg["mud_gain"], q=1.3),
            PeakFilter(cutoff_frequency_hz=cfg["presence_freq"], gain_db=cfg["presence_gain"], q=1.1),
            LowpassFilter(cutoff_frequency_hz=cfg["lp_cutoff"]),
            Compressor(
                threshold_db=cfg["comp_thresh"],
                ratio=cfg["comp_ratio"],
                attack_ms=5.0,
                release_ms=50.0
            ),
            Gain(gain_db=cfg["makeup_gain"]),
            Limiter(threshold_db=-1.0, release_ms=30.0)
        ]

        board = Pedalboard(chain)

        if callback:
            callback(75, "正在高精度渲染人聲特徵...")

        processed = board(audio, sr)

        if callback:
            callback(90, "儲存清晰化音訊...")

        with AudioFile(output_path, 'w', sr, processed.shape[0]) as out:
            out.write(processed)

        if callback:
            callback(100, "處理完成！")

class MorandiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AuraVoice ASR - 語音判讀聲音特化工具")
        self.geometry("680x680")
        self.resizable(False, False)

        # 莫蘭迪高雅色系
        self.C_BG = "#EAECE9"
        self.C_CARD = "#F5F6F4"
        self.C_PRIMARY = "#6D8271"
        self.C_PRIMARY_HOV = "#596D5D"
        self.C_SECONDARY = "#8896A0"
        self.C_TEXT = "#333A36"
        self.C_MUTED = "#757D78"
        self.C_BORDER = "#D6DBD5"
        self.C_GUIDE_BG = "#F0F2EF"

        self.configure(bg=self.C_BG)

        # 全介面採用標準微軟正黑體 (黑體)
        FONT_FAMILY = "Microsoft JhengHei UI"
        self.font_main = (FONT_FAMILY, 9)
        self.font_bold = (FONT_FAMILY, 9, "bold")
        self.font_title = (FONT_FAMILY, 15, "bold")
        self.font_guide = (FONT_FAMILY, 8)

        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.selected_preset = tk.StringVar(value="conference")

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure(".", background=self.C_BG, foreground=self.C_TEXT, font=self.font_main)
        style.configure("Morandi.TLabelframe", background=self.C_CARD, bordercolor=self.C_BORDER, relief="solid", borderwidth=1)
        style.configure("Morandi.TLabelframe.Label", background=self.C_CARD, foreground=self.C_TEXT, font=self.font_bold)
        style.configure("Morandi.TEntry", fieldbackground="#FFFFFF", foreground=self.C_TEXT, bordercolor=self.C_BORDER)

        style.configure("Morandi.TRadiobutton", background=self.C_CARD, foreground=self.C_TEXT, font=self.font_main)
        style.map("Morandi.TRadiobutton", background=[('active', self.C_CARD)])

        style.configure("Secondary.TButton", background=self.C_SECONDARY, foreground="#FFFFFF", borderwidth=0, font=self.font_main)
        style.map("Secondary.TButton", background=[('active', '#76848E')])

        style.configure("Primary.TButton", background=self.C_PRIMARY, foreground="#FFFFFF", borderwidth=0, font=self.font_bold)
        style.map("Primary.TButton", background=[('active', self.C_PRIMARY_HOV)])

        style.configure("Morandi.Horizontal.TProgressbar", troughcolor=self.C_BORDER, background=self.C_PRIMARY, bordercolor=self.C_BG, lightcolor=self.C_PRIMARY, darkcolor=self.C_PRIMARY)

    def build_ui(self):
        root = tk.Frame(self, bg=self.C_BG, padx=22, pady=16)
        root.pack(fill=tk.BOTH, expand=True)

        # 頂部標題
        head = tk.Frame(root, bg=self.C_BG)
        head.pack(fill=tk.X, pady=(0, 10))
        tk.Label(head, text="AuraVoice ASR 語音判讀聲音特化工具", font=self.font_title, fg=self.C_TEXT, bg=self.C_BG).pack(anchor=tk.W)
        tk.Label(head, text="專為語音辨識 (ASR) 優化：消除間隙底噪、提升咬字共振、保證不破音", font=self.font_main, fg=self.C_MUTED, bg=self.C_BG).pack(anchor=tk.W, pady=(2, 0))

        # 使用指南面板 (卡片樣式)
        guide_box = ttk.LabelFrame(root, text=" 📖 使用指南與判讀說明 ", style="Morandi.TLabelframe", padding="10")
        guide_box.pack(fill=tk.X, pady=(0, 10))

        guide_texts = (
            "1. 格式支援：支援常見影片 (MP4, MOV, MKV) 與音訊檔 (MP3, WAV, M4A)，會自動解碼並提取聲音軌。\n"
            "2. 場景選擇：若有冷氣或環境底噪請選「戶外／強噪」；演講與空曠房間選「室內會議」消除空洞感。\n"
            "3. 輸出建議：輸出預設為無損高保真 WAV，已加入 -1.0 dBFS 防削波，可直接匯入語音辨識模型 (ASR) 進行判讀。"
        )
        tk.Label(guide_box, text=guide_texts, justify=tk.LEFT, fg=self.C_TEXT, bg=self.C_CARD, font=self.font_guide, anchor="w").pack(fill=tk.X)

        # 檔案選取設定
        fbox = ttk.LabelFrame(root, text=" 來源檔案與輸出設定 ", style="Morandi.TLabelframe", padding="10")
        fbox.pack(fill=tk.X, pady=(0, 10))

        tk.Label(fbox, text="影音來源:", fg=self.C_TEXT, bg=self.C_CARD, font=self.font_bold).grid(row=0, column=0, sticky=tk.W, pady=3)
        ttk.Entry(fbox, textvariable=self.input_file, width=46, style="Morandi.TEntry").grid(row=0, column=1, padx=8, pady=3)
        ttk.Button(fbox, text="瀏覽檔案", style="Secondary.TButton", command=self.select_input).grid(row=0, column=2, pady=3)

        tk.Label(fbox, text="輸出儲存:", fg=self.C_TEXT, bg=self.C_CARD, font=self.font_bold).grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Entry(fbox, textvariable=self.output_file, width=46, style="Morandi.TEntry").grid(row=1, column=1, padx=8, pady=3)
        ttk.Button(fbox, text="變更位置", style="Secondary.TButton", command=self.select_output).grid(row=1, column=2, pady=3)

        # 場景模式選擇
        sbox = ttk.LabelFrame(root, text=" 請選擇強化場景 (已內建各場景最佳抗噪與咬字增強) ", style="Morandi.TLabelframe", padding="10")
        sbox.pack(fill=tk.X, pady=(0, 12))

        options = [
            ("conference", "室內會議／演講（消除回音空洞感、大幅清濁提亮）"),
            ("noisy",      "吵雜戶外／強噪（激進除噪、切除低頻風噪、人聲極致前推）"),
            ("distant",    "微弱耳語／遠距離（小聲自動放大、全面拉平動態音量）"),
            ("interview",  "清晰訪談／標準廣播（消除底噪、廣播主播級飽滿通透）")
        ]

        for i, (key, label) in enumerate(options):
            r = ttk.Radiobutton(sbox, text=label, value=key, variable=self.selected_preset, style="Morandi.TRadiobutton")
            r.grid(row=i, column=0, sticky=tk.W, pady=2)

        # 狀態與進度條
        self.status_label = tk.Label(root, text="就緒 (請載入欲優化的影音檔案)", font=self.font_main, fg=self.C_MUTED, bg=self.C_BG)
        self.status_label.pack(anchor=tk.W, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(root, style="Morandi.Horizontal.TProgressbar", orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 14))

        # 執行按鈕
        self.run_btn = ttk.Button(root, text="開始強效清晰優化 (專供語音辨識)", style="Primary.TButton", command=self.start_processing)
        self.run_btn.pack(fill=tk.X, ipady=5)

    def select_input(self):
        f = filedialog.askopenfilename(
            title="選擇影音檔案",
            filetypes=[
                ("所有影音格式", "*.mp4 *.mov *.mkv *.mp3 *.wav *.m4a *.flac *.aac *.ogg"),
                ("影片檔案", "*.mp4 *.mov *.mkv *.avi"),
                ("音訊檔案", "*.mp3 *.wav *.m4a *.flac"),
                ("所有檔案", "*.*")
            ]
        )
        if f:
            self.input_file.set(f)
            base, _ = os.path.splitext(f)
            self.output_file.set(f"{base}_distinct_asr.wav")
            self.status_label.config(text=f"已選取：{os.path.basename(f)}")

    def select_output(self):
        f = filedialog.asksaveasfilename(
            title="選擇儲存路徑",
            defaultextension=".wav",
            filetypes=[("高保真 WAV 音訊", "*.wav"), ("FLAC 無損", "*.flac")]
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
        preset = self.selected_preset.get()

        if not src or not os.path.exists(src):
            messagebox.showwarning("提示", "請先選擇有效的影音檔案！")
            return
        if not dst:
            messagebox.showwarning("提示", "請指定輸出檔案位置！")
            return

        self.run_btn.config(state=tk.DISABLED)

        def worker():
            try:
                DistinctASREngine.process_file(
                    src,
                    dst,
                    preset_key=preset,
                    callback=self.update_progress
                )
                messagebox.showinfo("完成", f"語音特化完成！\n輸出檔案：\n{dst}\n間隙底噪已消除，咬字清晰度已顯著拉大！")
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
