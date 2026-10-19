import os
import sys
import ctypes
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

# ----------------- 解決 Windows 介面模糊 (High DPI 銳利化修復) -----------------
def enable_high_dpi():
    """通知 Windows 系統不要用點陣強制拉大視窗，啟用原生高解析度渲染"""
    if sys.platform.startswith('win'):
        try:
            # Windows 10 1607+ / Windows 11: 逐螢幕 DPI 感知 (最清晰)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # 較早版本 Windows 備案
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

enable_high_dpi()
# ----------------------------------------------------------------------------

def get_resource_path(relative_path: str) -> str:
    """相容開發環境與 PyInstaller 打包後的解壓路徑"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class AudioClarifierEngine:
    @staticmethod
    def enhance_clarity(input_path: str, output_path: str, clarity_boost: float, callback=None):
        if callback:
            callback(15, "正在解碼並載入影音檔聲音軌...")

        with AudioFile(input_path) as f:
            audio = f.read(f.frames)
            sr = f.samplerate

        if callback:
            callback(35, "正在濾除超低頻底噪與雜音...")

        effects = [
            HighpassFilter(cutoff_frequency_hz=85.0),
            PeakFilter(cutoff_frequency_hz=280.0, gain_db=-2.5, q=1.0),
            PeakFilter(cutoff_frequency_hz=3200.0, gain_db=clarity_boost * 4.5, q=1.2),
            HighShelfFilter(cutoff_frequency_hz=8500.0, gain_db=clarity_boost * 3.0),
        ]

        if callback:
            callback(60, "正在套用動態壓縮平衡音量...")

        effects.extend([
            Compressor(threshold_db=-18.0, ratio=2.8, attack_ms=15.0, release_ms=80.0),
            Gain(gain_db=2.5),
            Limiter(threshold_db=-1.0, release_ms=50.0)
        ])

        board = Pedalboard(effects)

        if callback:
            callback(80
