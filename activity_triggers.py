import re
import time
import subprocess
import sys
import os

try:
    import psutil
except Exception:
    psutil = None

_pynput_mouse = None
_pynput_keyboard = None

from PySide6.QtCore import QObject, QTimer, QEvent, QPoint, QRect, Qt
import multiprocessing


class ActivityTriggerManager(QObject):
    """占位 ActivityTriggerManager，目前不执行任何气泡触发逻辑。"""

    def __init__(self, pet, dialogue_manager):
        super().__init__(pet)

        self.pet = pet
        self.dialogue_manager = dialogue_manager

        print("[ActivityTriggerManager] activity trigger features disabled")

    def eventFilter(self, watched, event):
        return super().eventFilter(watched, event)
