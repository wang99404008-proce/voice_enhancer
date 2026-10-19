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

class ASROptimizerEngine:
    """專為語音辨識/判讀特化的聲音清晰化引擎"""
    PRESETS = {
        "conference": {
            "name": "室內會議與演講 (消除房間殘響、加強咬字共振)",
            "hp_cutoff": 90.0,
            "lp_cutoff": 7800.0,
            "mud_freq": 280.0,
            "mud_gain": -3.5,
            "voice_freq": 3200.0,
            "voice_gain": 4.5,
            "comp_thresh": -18.0,
            "comp_ratio": 3.0,
            "boost_gain": 3.0
        },
        "noisy": {
            "name": "戶外與吵雜環境 (強效除噪、低頻截斷、人聲凸顯)",
            "hp_cutoff": 130.0,
            "lp_cutoff": 7500.0,
            "mud_freq": 350.0,
            "mud_gain": -4.0,
            "voice_freq": 2800.0,
            "voice_gain": 5.5,
            "comp_thresh": -20.0,
            "comp_ratio": 3.5,
            "boost_gain": 3.5
        },
        "distant": {
            "name": "遠距微弱語音 (提升微弱發音、深度動態拉平)",
            "hp_cutoff": 100.0,
            "lp_cutoff": 8000.0,
            "mud_freq": 300.0,
            "mud_gain": -2.0,
            "voice_freq": 3000.0,
            "voice_gain": 5.0,
            "comp_thresh": -24.0,
            "comp_ratio": 4.5,
            "boost_gain": 5.0
        },
        "interview": {
            "name": "清晰訪談與對話 (全頻段均衡、高保真發音辨識)",
            "hp_cutoff": 80.0,
            "lp_cutoff": 8500.0,
            "mud_freq": 250.0,
            "mud_gain": -2.5,
            "voice_freq": 3400.0,
            "voice_gain": 3.5,
            "comp_thresh": -16.0,
            "comp_ratio": 2.5,
            "boost_gain": 2.5
        }
    }

    @classmethod
    def enhance_for_asr(cls, input_path: str, output_path: str, preset_key: str, callback=None):
        cfg = cls.PRESETS.get(preset_key, cls.PRESETS["conference"])

        if callback:
            callback(15, "正在解碼多媒體音軌...")

        with AudioFile(input_path) as f:
            audio = f.read(f.frames)
            sr = f.samplerate

        if callback:
            callback(35, f"套用【{cfg['name']}】頻段雕刻...")

        chain = [
            HighpassFilter(cutoff_frequency_hz=cfg["hp_cutoff"]),
            LowpassFilter(cutoff_frequency_hz=cfg["lp_cutoff"]),
            PeakFilter(cutoff_frequency_hz=cfg["mud_freq"], gain_db=cfg["mud_gain"], q=1.2),
            PeakFilter(cutoff_frequency_hz=cfg["voice_freq"], gain_db=cfg["voice_gain"], q=1.1),
            Compressor(
                threshold_db=cfg["comp_thresh"],
                ratio=cfg["comp_ratio"],
                attack_ms=8.0,
                release_ms=60.0
            ),
            Gain(gain_db=cfg["boost_gain"]),
            Limiter(threshold_db=-1.0, release_ms=30.0)
        ]

        board = Pedalboard(chain)

        if callback:
            callback(75, "計算語音特徵渲染中...")

        processed = board(audio, sr)

        if callback:
            callback(90, "儲存高品質判讀音訊...")

        with AudioFile(output_path, 'w', sr, processed.shape[0]) as out:
            out.write(processed)

        if callback:
            callback(100, "判讀特化優化完成！")

class MorandiASRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AuraVoice ASR - 語音判讀聲音特化工具")
        self.geometry("640x510")
        self.resizable(False, False)

        # 莫蘭迪高雅色調
        self.C_BG = "#EAECE9"
        self.C_CARD = "#F5F6F4"
        self.C_PRIMARY = "#718575"       # 灰綠
        self.C_PRIMARY_HOV = "#5D6F61"
        self.C_SECONDARY = "#8B99A3"     # 霧灰藍
        self.C_TEXT = "#333A36"
        self.C_MUTED = "#757D78"
        self.C_BORDER = "#D8DCD7"

        self.configure(bg=self.C_BG)

        # 統一設定為標準黑體 (Microsoft JhengHei UI)
        FONT_FAMILY = "Microsoft JhengHei UI"
        self.font_main = (FONT_FAMILY, 9)
        self.font_bold = (FONT_FAMILY, 9, "bold")
        self.font_title = (FONT_FAMILY, 15, "bold")

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
        root = tk.Frame(self, bg=self.C_BG, padx=24, pady=20)
        root.pack(fill=tk.BOTH, expand=True)

        # 頂部標題
        head = tk.Frame(root, bg=self.C_BG)
        head.pack(fill=tk.X, pady=(0, 14))
        tk.Label(head, text="AuraVoice ASR 語音特化增強", font=self.font_title, fg=self.C_TEXT, bg=self.C_BG).pack(anchor=tk.W)
        tk.Label(head, text="針對不同錄音環境提升語音辨識率，防削波且無需手動微調", font=self.font_main, fg=self.C_MUTED, bg=self.C_BG).pack(anchor=tk.W, pady=(2, 0))

        # 檔案路徑卡片
        fbox = ttk.LabelFrame(root, text=" 來源檔案與輸出設定 ", style="Morandi.TLabelframe", padding="12")
        fbox.pack(fill=tk.X, pady=(0, 12))

        tk.Label(fbox, text="影音來源:", fg=self.C_TEXT, bg=self.C_CARD, font=self.font_bold).grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(fbox, textvariable=self.input_file, width=42, style="Morandi.TEntry").grid(row=0, column=1, padx=8, pady=4)
        ttk.Button(fbox, text="瀏覽檔案", style="Secondary.TButton", command=self.select_input).grid(row=0, column=2, pady=4)

        tk.Label(fbox, text="輸出儲存:", fg=self.C_TEXT, bg=self.C_CARD, font=self.font_bold).grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(fbox, textvariable=self.output_file, width=42, style="Morandi.TEntry").grid(row=1, column=1, padx=8, pady=4)
        ttk.Button(fbox, text="變更位置", style="Secondary.TButton", command=self.select_output).grid(row=1, column=2, pady=4)

        # 場景模式選擇卡片
        sbox = ttk.LabelFrame(root, text=" 請選擇錄音環境場景 (自動套用最高辨識調校) ", style="Morandi.TLabelframe", padding="12")
        sbox.pack(fill=tk.X, pady=(0, 14))

        options = [
            ("conference", "室內會議與演講 (消除房間殘響、加強咬字共振)"),
            ("noisy",      "戶外與吵雜環境 (強效截除車流與環境噪聲、凸顯人聲)"),
            ("distant",    "遠距微弱語音 (提升微弱發音、深度動態拉平)"),
            ("interview",  "清晰訪談與對話 (全頻段均衡、高保真發音辨識)")
        ]

        for i, (key, label) in enumerate(options):
            r = ttk.Radiobutton(sbox, text=label, value=key, variable=self.selected_preset, style="Morandi.TRadiobutton")
            r.grid(row=i, column=0, sticky=tk.W, pady=3)

        # 狀態與進度條
        self.status_label = tk.Label(root, text="就緒 (請載入欲辨識的影音檔案)", font=self.font_main, fg=self.C_MUTED, bg=self.C_BG)
        self.status_label.pack(anchor=tk.W, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(root, style="Morandi.Horizontal.TProgressbar", orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 16))

        # 執行按鈕
        self.run_btn = ttk.Button(root, text="開始特化清晰優化 (專供語音辨識)", style="Primary.TButton", command=self.start_processing)
        self.run_btn.pack(fill=tk.X, ipady=5)

    def select_input(self):
        f = filedialog.askopenfilename(
            title="選擇影片或音訊檔案",
            filetypes=[
                ("所有常見格式", "*.mp4 *.mov *.mkv *.mp3 *.wav *.m4a *.flac *.aac *.ogg"),
                ("影片檔案", "*.mp4 *.mov *.mkv *.avi"),
                ("音訊檔案", "*.mp3 *.wav *.m4a *.flac"),
                ("所有檔案", "*.*")
            ]
        )
        if f:
            self.input_file.set(f)
            base, _ = os.path.splitext(f)
            self.output_file.set(f"{base}_for_asr.wav")
            self.status_label.config(text=f"已選取：{os.path.basename(f)}")

    def select_output(self):
        f = filedialog.asksaveasfilename(
            title="選擇輸出路徑",
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
            messagebox.showwarning("提示", "請先選擇有效的來源檔案！")
            return
        if not dst:
            messagebox.showwarning("提示", "請指定輸出檔案位置！")
            return

        self.run_btn.config(state=tk.DISABLED)

        def worker():
            try:
                ASROptimizerEngine.enhance_for_asr(
                    src,
                    dst,
                    preset_key=preset,
                    callback=self.update_progress
                )
                messagebox.showinfo("完成", f"語音特化完成！\n優化音訊已儲存至：\n{dst}\n可直接提供給語音辨識模型使用。")
            except Exception as e:
                messagebox.showerror("錯誤", f"處理失敗：\n{str(e)}")
            finally:
                self.run_btn.config(state=tk.NORMAL)
                self.status_label.config(text="就緒")
                self.progress_bar['value'] = 0

        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = MorandiASRApp()
    app.mainloop()
