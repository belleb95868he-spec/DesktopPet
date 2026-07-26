import random
import time

from PySide6.QtCore import QTimer


class PettingManager:
    """管理点击头部两次触发的摸摸互动。"""

    # 两次点击相隔不超过 700ms，视为一次摸摸
    DOUBLE_CLICK_INTERVAL = 0.70

    # 两次点击相隔不超过 220ms，视为点得太快并触发害羞
    SHY_CLICK_INTERVAL = 0.22

    # 头部区域占人物图片高度的比例
    HEAD_AREA_RATIO = 0.46

    def __init__(self, pet):
        self.pet = pet
        self.first_click_time = None
        self.locked = False

        self.reset_timer = QTimer(self.pet)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_clicks)

        self.unlock_timer = QTimer(self.pet)
        self.unlock_timer.setSingleShot(True)
        self.unlock_timer.timeout.connect(self.unlock)

        self.normal_messages = [
            "被摸摸了，好开心！✨",
            "嘿嘿，再摸一下也可以～",
            "头发没有乱掉吧？",
        ]

        self.shy_messages = [
            "别、别摸这么快啦……///",
            "等一下！突然这样会害羞的……",
            "呜……心跳都变快了！",
        ]

    def is_head_position(self, local_position):
        """判断点击位置是否位于人物头部区域。"""
        head_limit = self.pet.pet_label.height() * self.HEAD_AREA_RATIO
        return local_position.y() <= head_limit

    def register_head_click(self):
        """记录一次头部点击；第二次点击时判断普通摸摸或害羞。"""
        if self.locked or self.pet.is_interaction_locked():
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

        self.locked = True
        self.unlock_timer.start(650)

        if interval <= self.SHY_CLICK_INTERVAL:
            self.trigger_shy()
        else:
            self.trigger_normal_petting()

    def trigger_normal_petting(self):
        if self.pet.is_interaction_locked():
            return
        self.pet.dialogue_manager.show_message(
            random.choice(self.normal_messages),
            duration=3000,
        )
        self.pet.status_manager.increase_mood(
            amount=10,
            show_message=False,
        )

    def trigger_shy(self):
        if self.pet.is_interaction_locked():
            return
        self.pet.dialogue_manager.show_message(
            random.choice(self.shy_messages),
            duration=3500,
        )
        self.pet.status_manager.increase_mood(
            amount=15,
            show_message=False,
        )

    def reset_clicks(self):
        self.first_click_time = None

    def unlock(self):
        self.locked = False
