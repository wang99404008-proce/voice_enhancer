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
    """專為語音辨識/判讀特化的人聲清晰引擎"""
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
        # 視窗外框名稱改為【人聲清晰特化】
        self.title("人聲清晰特化")
        self.geometry("680x680")
        self.resizable(False, False)

        # 莫蘭迪色系配置
        self.C_BG = "#EAECE9"
        self.C_CARD = "#F5F6F4"
        self.C_PRIMARY = "#6D8271"
        self.C_PRIMARY_HOV = "#596D5D"
        self.C_SECONDARY = "#8896A0"
        self.C_TEXT = "#333A36"
        self.C_MUTED = "#757D78"
        self.C_BORDER = "#D6DBD5"

        self.configure(bg=self.C_BG)

        # 統一黑體 (Microsoft JhengHei UI)
        FONT_FAMILY = "Microsoft JhengHei UI"
        self.font_main = (FONT_FAMILY, 9)
        self.font_bold = (FONT_FAMILY, 9, "bold")
        self.font_title = (FONT_FAMILY, 16, "bold")
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

        style.configure("Morandi
