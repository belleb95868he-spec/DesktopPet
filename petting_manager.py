import random
import time

from PySide6.QtCore import QTimer


class PettingManager:
    """管理点击头部两次触发的摸摸互动。"""

    # 两次点击相隔不超过 700ms，视为一次摸摸
    DOUBLE_CLICK_INTERVAL = 0.70

    # 头部区域占人物图片高度的比例
    HEAD_AREA_RATIO = 0.46

    def __init__(self, pet):
        self.pet = pet
        self.first_click_time = None

        self.reset_timer = QTimer(self.pet)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_clicks)

        self.messages = [
            "嗯？怎么了？",
            "有什么好事吗？",
            "头发没有乱掉吧？",
            "好啦好啦",
            "怎么突然摸我的大头",
            "我在我在",
        ]

    def is_head_position(self, local_position):
        """判断点击位置是否位于人物头部区域。"""
        head_limit = self.pet.pet_label.height() * self.HEAD_AREA_RATIO
        return local_position.y() <= head_limit

    def register_head_click(self):
        """记录头部点击；每次有效双击增加心情并刷新对话。"""
        if self.pet.animation_manager.current_state == "work":
            return

        now = time.monotonic()

        if self.first_click_time is None:
            self.first_click_time = now
            self.reset_timer.start(
                int(self.DOUBLE_CLICK_INTERVAL * 1000)
            )
            return

        interval = now - self.first_click_time
        self.reset_timer.stop()
        self.first_click_time = None

        if interval > self.DOUBLE_CLICK_INTERVAL:
            # 距离太久，把本次当作新一轮的第一次点击
            self.first_click_time = now
            self.reset_timer.start(
                int(self.DOUBLE_CLICK_INTERVAL * 1000)
            )
            return

        self.trigger_petting()

    def trigger_petting(self):
        """动画只在空闲时启动；动画中双击仍会增加心情和更新对话。"""
        self.pet.animation_manager.start_petting()
        self.pet.dialogue_manager.show_message(
            random.choice(self.messages),
            duration=3000,
            allow_during_petting=True,
        )
        self.pet.status_manager.increase_mood(
            amount=10,
            show_message=False,
            allow_during_petting=True,
        )

    def reset_clicks(self):
        self.first_click_time = None
