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
    """
    專為語音辨識 / 判讀特化的聲音清晰化引擎
    所有模式均以最大化模型特徵提取精度為基準，嚴格杜絕破音。
    """
    PRESETS = {
        "conference": {
            "name": "🏢 室內會議與演講 (去回音濁音、提亮咬字)",
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
            "name": "🚗 戶外與吵雜環境 (強效除噪、低頻截斷、人聲凸顯)",
            "hp_cutoff": 130.0,     # 激進截除車流、風聲與冷氣低頻
            "lp_cutoff": 7500.0,     # 去除高頻雜訊
            "mud_freq": 350.0,
            "mud_gain": -4.0,
            "voice_freq": 2800.0,
            "voice_gain": 5.5,      # 強烈突出咬字共振峰
            "comp_thresh": -20.0,
            "comp_ratio": 3.5,
            "boost_gain": 3.5
        },
        "distant": {
            "name": "🎙️ 遠距微弱人聲 (微弱音量增強、深度動態拉平)",
            "hp_cutoff": 100.0,
            "lp_cutoff": 8000.0,
            "mud_freq": 300.0,
            "mud_gain": -2.0,
            "voice_freq": 3000.0,
            "voice_gain": 5.0,
            "comp_thresh": -24.0,    # 低門檻抓取微弱發音
            "comp_ratio": 4.5,      # 高壓縮比壓平動態
            "boost_gain": 5.0
        },
        "interview": {
            "name": "🎧 清晰訪談與播客 (標準廣播級人聲、平衡高辨識度)",
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

        # 針對語音判讀建構濾波鏈
        chain = [
            # 1. 濾除對辨識無益甚至有害的超低頻震動與嗡鳴
            HighpassFilter(cutoff_frequency_hz=cfg["hp_cutoff"]),
            # 2. 濾除高頻無效雜訊（讓模型專注於 8kHz 以下語音帶）
            LowpassFilter(cutoff_frequency_hz=cfg["lp_cutoff"]),
            # 3. 精準消除讓說話發悶的頻段
            PeakFilter(cutoff_frequency_hz=cfg["mud_freq"], gain_db=cfg["mud_gain"], q=1.2),
            # 4. 關鍵音素增強（凸顯咬字特徵點）
            PeakFilter(cutoff_frequency_hz=cfg["voice_freq"], gain_db=cfg["voice_gain"], q=1.1),
            # 5. 平衡語音起伏（避免大聲爆音、小聲遺漏）
            Compressor(
                threshold_db=cfg["comp_thresh"],
                ratio=cfg["comp_ratio"],
                attack_ms=8.0,
                release_ms=60.0
            ),
            # 6. 音量增益補償
            Gain(gain_db=cfg["boost_gain"]),
            # 7. 廣播級極限器：鎖死在 -1.0 dBFS，保證絕對不失真爆音
            Limiter(threshold_db=-1.0, release_ms=30.0)
        ]

        board = Pedalboard(chain)

        if callback:
            callback(75, "計算語音特徵渲染中...")

        processed = board(audio, sr)

        if callback:
            callback(90, "儲存高品質判讀音訊...")

        # 轉存無損 WAV 供辨識模型讀取
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

        self.font_main = ("Microsoft JhengHei UI", 9)
        self
