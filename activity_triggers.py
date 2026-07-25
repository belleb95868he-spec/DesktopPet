import time
import subprocess
import sys

try:
    import psutil
except Exception:
    psutil = None

from PySide6.QtCore import QObject, QTimer, QEvent


class ActivityTriggerManager(QObject):
    """监控系统/应用与用户行为，并触发一次性对话气泡，带冷却时间。

    说明：尽量保持对原有架构无侵入；该管理器会作为 QObject 安装为
    应用级的事件过滤器以捕获在应用内的鼠标/键盘事件，同时通过轮询
    方式检测常见进程（Photoshop/After Effects/VSCode/音乐/聊天）与
    Chrome 标签数/YouTube 页面。
    """

    def __init__(self, pet, dialogue_manager):
        super().__init__(pet)

        self.pet = pet
        self.dialogue_manager = dialogue_manager

        # 30 分钟冷却（秒）
        self.cooldown = 30 * 60

        # 记录每种事件上次触发时间
        self.last_triggered = {}

        # 记录最后一次用户在应用内的输入时间（秒）
        self.last_input_time = time.time()

        # 连续点击不受冷却限制；在应用内每次点击都会弹出
        self.click_message = "路要一步一步走，饭要一口一口吃～"

        # 长时间未点击的提示（秒），默认 5 分钟
        self.idle_threshold = 5 * 60
        self.idle_message = "睡着了吗？"

        # 拖动检测（应用内拖动桌宠）
        self.drag_events = []
        self.drag_threshold_count = 8
        self.drag_window_seconds = 5
        self.drag_message = "头好晕！"

        # 恢复（从 sleep）检测：如果轮询间隔出现大于阈值的时间跳变，则认为刚从休眠恢复
        self.last_poll_time = time.time()
        self.wake_threshold = 60
        self.wake_message = "你终于回来了！"

        # 浏览器相关消息
        self.youtube_messages = [
            "有什么好看的视频吗，我也要看",
            "好多英文啊",
        ]

        # 进程名称到消息映射（尽力匹配常见进程名）
        self.process_map = [
            ("photoshop", ["Photoshop", "Adobe Photoshop"], "今天画什么呀？"),
            ("after_effects", ["After Effects", "Adobe After Effects", "AfterFX"], "今天要做什么动画吗！"),
            ("vscode", ["Code", "Visual Studio Code"], "不要一运行就报错呀～"),
            ("qqmusic", ["QQMusic", "qqmusic"], "在你最爱的巷弄～"),
            ("netease", ["cloudmusic", "NeteaseCloudMusic", "netease"], "在你最爱的巷弄～"),
            ("wechat", ["WeChat", "wechat"], "偷看你的聊天记录～"),
            ("qq", ["QQ", "qq"], "偷看你的聊天记录～"),
        ]

        # 轮询检测间隔（秒）
        self.poll_interval = 10

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(self.poll_interval * 1000)
        self.poll_timer.timeout.connect(self._poll_system)
        self.poll_timer.start()

        # 空闲检查定时器（每分钟检查一次）
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(60 * 1000)
        self.idle_timer.timeout.connect(self._check_idle)
        self.idle_timer.start()

        # 安装为应用级事件过滤器以捕获在应用内的鼠标/键盘事件
        app = None
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
        except Exception:
            app = None

        if app is not None:
            app.installEventFilter(self)

    def _can_trigger(self, key):
        last = self.last_triggered.get(key)

        if last is None:
            return True

        return (time.time() - last) >= self.cooldown

    def _mark_triggered(self, key):
        self.last_triggered[key] = time.time()

    def _poll_system(self):
        now = time.time()
        # 检测休眠/唤醒（轮询间隔出现大跳变）
        if now - self.last_poll_time > self.wake_threshold:
            if self._can_trigger("wake"):
                self.dialogue_manager.show_message(self.wake_message)
                self._mark_triggered("wake")

        self.last_poll_time = now

        # 检查进程列表
        procs = []

        if psutil:
            try:
                for p in psutil.process_iter(attrs=["name", "cmdline"]):
                    name = (p.info.get("name") or "")
                    cmd = " ".join(p.info.get("cmdline") or [])
                    procs.append((name, cmd))
            except Exception:
                procs = []

        # 对每个映射项检测是否存在进程
        for key, names, message in self.process_map:
            found = False

            for name, cmd in procs:
                lname = name.lower()
                lcmd = cmd.lower()

                for n in names:
                    if n.lower() in lname or n.lower() in lcmd:
                        found = True
                        break

                if found:
                    break

            if found and self._can_trigger(key):
                self.dialogue_manager.show_message(message)
                self._mark_triggered(key)

        # 检查浏览器中是否有 YouTube 标签
        try:
            if self._has_youtube_tab():
                if self._can_trigger("youtube"):
                    import random

                    msg = random.choice(self.youtube_messages)
                    self.dialogue_manager.show_message(msg)
                    self._mark_triggered("youtube")
        except Exception:
            pass

        # 检查 Chrome 标签数是否超过 10
        try:
            tab_count = self._get_chrome_tab_count()

            if tab_count is not None and tab_count > 10:
                if self._can_trigger("many_tabs"):
                    self.dialogue_manager.show_message("你今天很忙吗？")
                    self._mark_triggered("many_tabs")
        except Exception:
            pass

    def _get_chrome_tab_count(self):
        """尝试通过 AppleScript 读取 Google Chrome 的所有标签页数（macOS）。"""
        if sys.platform != "darwin":
            return None

        script = (
            'tell application "Google Chrome"\n'
            'set total to 0\n'
            'repeat with w in windows\n'
            'set total to total + (count of tabs of w)\n'
            'end repeat\n'
            'return total\n'
            'end tell'
        )

        try:
            out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL)
            text = out.decode().strip()

            return int(text)
        except Exception:
            return None

    def _has_youtube_tab(self):
        if sys.platform != "darwin":
            return False

        # 检查 Google Chrome
        script = (
            'tell application "Google Chrome"\n'
            'repeat with w in windows\n'
            'repeat with t in tabs of w\n'
            'if (URL of t) contains "youtube.com" then\n'
            'return true\n'
            'end if\n'
            'end repeat\n'
            'end repeat\n'
            'return false\n'
            'end tell'
        )

        try:
            out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL)
            text = out.decode().strip().lower()
            return text == "true"
        except Exception:
            return False

    def _check_idle(self):
        # 如果超过 idle_threshold 且未在冷却期内，触发一次
        now = time.time()

        if now - self.last_input_time > self.idle_threshold:
            if self._can_trigger("idle"):
                self.dialogue_manager.show_message(self.idle_message)
                self._mark_triggered("idle")

    # 应用级事件过滤器
    def eventFilter(self, watched, event):
        et = event.type()

        # 鼠标点击：更新最后输入时间，并对每次点击弹出无冷却气泡
        if et == QEvent.MouseButtonPress:
            self.last_input_time = time.time()

            # 连续点击不受冷却限制，直接显示
            self.dialogue_manager.show_message(self.click_message)

        # 鼠标移动（用于检测快速拖动桌宠）
        if et == QEvent.MouseMove:
            # 记录最近的拖动事件时间戳
            t = time.time()
            self.drag_events.append(t)

            # 丢弃过期事件
            cutoff = t - self.drag_window_seconds
            self.drag_events = [x for x in self.drag_events if x >= cutoff]

            if len(self.drag_events) >= self.drag_threshold_count:
                if self._can_trigger("dragging"):
                    self.dialogue_manager.show_message(self.drag_message)
                    self._mark_triggered("dragging")

        # 键盘按键也计为用户输入
        if et == QEvent.KeyPress:
            self.last_input_time = time.time()

        return super().eventFilter(watched, event)
