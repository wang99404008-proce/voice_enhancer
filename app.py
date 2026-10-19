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
    """
    強效有感語音判讀優化引擎：
    - 引入 NoiseGate 消除字句間隙底噪（對比極為顯著）
    - 大幅度加深濁音切除與共振峰咬字突出
    - 廣播級極限制，音量飽滿且絕對不削波
    """
    PRESETS = {
        "conference": {
            "name": "室內會議／演講（消除回音空洞感、大幅清濁提亮）",
            "hp_cutoff": 120.0,
            "lp_cutoff": 7500.0,
            "gate_thresh": -38.0,    # 消除室內冷氣底噪與遠處雜音
            "mud_freq": 320.0,
            "mud_gain": -6.0,        # 大幅切除悶音
            "presence_freq": 3200.0,
            "presence_gain": 6.5,    # 大幅凸顯咬字
            "comp_thresh": -20.0,
            "comp_ratio": 4.5,
            "makeup_gain": 4.0
        },
        "noisy": {
            "name": "吵雜戶外／強噪（激進除噪、切除低頻風噪、人聲極致前推）",
            "hp_cutoff": 160.0,      # 強制切除所有車流與低頻震動
            "lp_cutoff": 7000.0,
            "gate_thresh": -32.0,    # 強力噪聲門，非說話時完全靜音
            "mud_freq": 380.0,
            "mud_gain": -8.0,
            "presence_freq": 2800.0,
            "presence_gain": 8.0,    # 極度突出母音共振峰
            "comp_thresh": -24.0,
            "comp_ratio": 6.0,
            "makeup_gain": 5.5
        },
        "distant": {
            "name": "微弱耳語／遠距離（小聲自動放大 300%、全面拉平音量）",
            "hp_cutoff": 100.0,
            "lp_cutoff": 8000.0,
            "gate_thresh": -46.0,    # 放寬門檻以免吃掉微弱字尾
            "mud_freq": 280.0,
            "mud_gain": -4.0,
            "presence_freq": 3400.0,
            "presence_gain": 7.0,
            "comp_thresh": -28.0,    # 極深抓取弱音
            "comp_ratio": 6.5,      # 深度拉平動態
            "makeup_gain": 7.0
        },
        "interview": {
            "name": "清晰訪談／標準廣播（乾淨底噪、廣播主播級飽滿通透）",
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

        # 建構高對比度處理鏈
        chain = [
            # 1. 強效高通 (截斷冷氣、震動)
            HighpassFilter(cutoff_frequency_hz=cfg["hp_cutoff"]),
            
            # 2. 噪聲門限 (關鍵有感：講話停頓處的底噪全部砍掉)
            NoiseGate(
                threshold_db=cfg["gate_thresh"],
                ratio=10.0,
                attack_ms=5.0,
                release_ms=80.0
            ),
            
            # 3. 激進切除發悶的渾濁區
            PeakFilter(cutoff_frequency_hz=cfg["mud_freq"], gain_db=cfg["mud_gain"], q=1.3),
            
            # 4. 強效增強子音咬字清晰度
            PeakFilter(cutoff_frequency_hz=cfg["presence_freq"], gain_db=cfg["presence_gain"], q=1.1),
            
            # 5. 低通濾波消除刺耳超高頻噪訊
            LowpassFilter(cutoff_frequency_hz=cfg["lp_cutoff"]),
            
            # 6. 廣播級平準壓縮器 (將微弱字詞瞬間拉高)
            Compressor(
                threshold_db=cfg["comp_thresh"],
                ratio=cfg["comp_ratio"],
                attack_ms=5.0,
                release_ms=50.0
            ),
            
            # 7. 明顯的輸出增益補償
            Gain(gain_db=cfg["makeup_gain"]),
            
            # 8. 安全牆防破音 (鎖死在 -1.0 dBFS)
            Limiter(threshold_db=-1.0, release_ms=30.0)
        ]

        board = Pedalboard(chain)

        if callback:
            callback(75, "正在高精度渲染人聲軌...")

        processed = board(audio, sr)

        if callback:
            callback(90, "儲存清晰化音訊...")

        with AudioFile(output_path, 'w', sr, processed.shape[0]) as out:
            out.write(processed)

        if callback:
            callback(100, "處理完成！前後差異顯著。")

class MorandiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AuraVoice ASR - 強效聲音清晰特化工具")
        self.geometry("650x530")
        self.resizable(False, False)

        # 莫蘭迪灰綠色系
        self.C_BG = "#EAECE9"
        self.C_CARD = "#F5F6F4"
        self.C_PRIMARY = "#6D8271"
        self.C_PRIMARY_HOV = "#596D5D"
        self.C_SECONDARY = "#8896A0"
        self.C_TEXT = "#333A36"
        self.C_MUTED = "#757D78"
        self.C_BORDER = "#D6DBD5"

        self.configure(bg=self.C_BG)

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

        head = tk.Frame(root, bg=self.C_BG)
        head.pack(fill=tk.X, pady=(0, 14))
        tk.Label(head, text="AuraVoice ASR 語音特化增強", font=self.font_title, fg=self.C_TEXT, bg=self.C_BG).pack(anchor=tk.W)
        tk.Label(head, text="內建噪聲門與強效人聲平準化，消除間隙底噪、咬字顯著清晰", font=self.font_main, fg=self.C_MUTED, bg=self.C_BG).pack(anchor=tk.W, pady=(2, 0))

        # 檔案路徑
        fbox = ttk.LabelFrame(root, text=" 來源檔案與輸出設定 ", style="Morandi.TLabelframe", padding="12")
        fbox.pack(fill=tk.X, pady=(0, 12))

        tk.Label(fbox, text="影音來源:", fg=self.C_TEXT, bg=self.C_CARD, font=self.font_bold).grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(fbox, textvariable=self.input_file, width=44, style="Morandi.TEntry").grid(row=0, column=1, padx=8, pady=4)
        ttk.Button(fbox, text="瀏覽檔案", style="Secondary.TButton", command=self.select_input).grid(row=0, column=2, pady=4)

        tk.Label(fbox, text="輸出儲存:", fg=self.C_TEXT, bg=self.C_CARD, font=self.font_bold).grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(fbox, textvariable=self.output_file, width=44, style="Morandi.TEntry").grid(row=1, column=1, padx=8, pady=4)
        ttk.Button(fbox, text="變更位置", style="Secondary.TButton", command=self.select_output).grid(row=1, column=2, pady=4)

        # 場景模式
        sbox = ttk.LabelFrame(root, text=" 請選擇強化場景 (已配置噪聲門與人聲共振放大) ", style="Morandi.TLabelframe", padding="12")
        sbox.pack(fill=tk.X, pady=(0, 14))

        options = [
            ("conference", "室內會議／演講（消除回音空洞感、大幅清濁提亮）"),
            ("noisy",      "吵雜戶外／強噪（激進除噪、切除低頻風噪、人聲極致前推）"),
            ("distant",    "微弱耳語／遠距離（小聲自動放大 300%、全面拉平音量）"),
            ("interview",  "清晰訪談／標準廣播（乾淨底噪、廣播主播級飽滿通透）")
        ]

        for i, (key, label) in enumerate(options):
            r = ttk.Radiobutton(sbox, text=label, value=key, variable=self.selected_preset, style="Morandi.TRadiobutton")
            r.grid(row=i, column=0, sticky=tk.W, pady=3)

        self.status_label = tk.Label(root, text="就緒 (請先匯入影音檔案)", font=self.font_main, fg=self.C_MUTED, bg=self.C_BG)
        self.status_label.pack(anchor=tk.W, pady=(0, 4))

        self.progress_bar = ttk.Progressbar(root, style="Morandi.Horizontal.TProgressbar", orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 16))

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
