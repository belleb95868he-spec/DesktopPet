import random
from datetime import datetime

from PySide6.QtCore import QObject, QTimer


class HourlyGreetingManager(QObject):
    """根据当前整点自动让桌宠说话。"""

    def __init__(self, pet, dialogue_manager):
        super().__init__(pet)

        self.pet = pet
        self.dialogue_manager = dialogue_manager

        # 记录上一次已经说过话的小时
        # 避免同一个小时重复触发
        self.last_triggered_key = None

        # 每个小时对应的台词
        self.hourly_messages = {
            0: [
                "又是新的一天～早点睡吧"
            ],
            1: [
                "你还不睡觉吗，在想什么"
            ],
            2: [
                "你怎么还在电脑桌前？"
            ],
            3: [
                "真的该去睡觉咯"
            ],
            4: [
                "不想睡就不勉强睡了，听听我的歌吧"
            ],
            5: [
                "天蒙蒙亮了"
            ],
            6: [
                "你起的好早啊，还是说没睡？"
            ],
            7: [
                "来一杯拿铁吧！"
            ],
            8: [
                "今天要上班吗？加油哦"
            ],
            9: [
                "你准备要出门了吗？注意安全"
            ],
            10: [
                "今天你在家陪我吗？"
            ],
            11: [
                "你想吃什么，我去准备煮午餐！"
            ],
            12: [
                "我在为了下场演唱会减肥呢"
            ],
            13: [
                "你喜欢听红装对吗，我唱给你听！"
            ],
            14: [
                "没话讲～我们互相在假装～你的电话还在响～"
            ],
            15: [
                "我要去听一下学员的歌了"
            ],
            16: [
                "你觉得下一条抖音我拍这个怎么样？"
            ],
            17: [
                "现在的演唱会人心黄黄的～"
            ],
            18: [
                "不要小看名字里带良的人～"
            ],
            19: [
                "大家唱的也太好了，真棒！"
            ],
            20: [
                "等不到你的雪月风花，我们的爱有时差～"
            ],
            21: [
                "我该去给学生们上课了，等等回来"
            ],
            22: [
                "我想点一碗面吃"
            ],
            23: [
                "你还在工作吗？我今天也要加班"
            ],
        }

        # 每 10 秒检查一次时间
        # 不需要每秒检查，减少无意义调用
        self.check_timer = QTimer(self)
        self.check_timer.setInterval(10_000)

        self.check_timer.timeout.connect(
            self.check_current_time
        )

        self.check_timer.start()

        # 程序启动时立即检查一次
        self.check_current_time()

    def get_message_for_hour(self, hour):
        """根据小时返回一条对应台词。"""

        messages = self.hourly_messages.get(hour)

        if not messages:
            return None

        return random.choice(messages)

    def test_greeting(self, hour):
        """手动测试指定小时的台词。"""

        message = self.get_message_for_hour(hour)

        if message:
            print("[hourly_greeting] test_greeting:", message)
            self.dialogue_manager.show_message(
                message,
                duration=7000
            )

        return message

    def check_current_time(self):
        """检查现在是否到了新的整点。"""

        now = datetime.now()

        # 只有整点后的前两分钟触发
        # 防止程序在 14:37 启动时突然说 14 点台词
        if now.minute > 1:
            return

        # 用日期和小时组成唯一标记
        # 例如：2026-07-25-14
        trigger_key = (
            now.year,
            now.month,
            now.day,
            now.hour
        )

        # 当前小时已经触发过，不再重复
        if trigger_key == self.last_triggered_key:
            return

        message = self.get_message_for_hour(now.hour)

        if not message:
            return

        print("[hourly_greeting] trigger:", now.hour, message)
        self.dialogue_manager.show_message(
            message,
            duration=7000
        )

        self.last_triggered_key = trigger_key