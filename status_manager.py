import json
from pathlib import Path

from PySide6.QtCore import QTimer


class StatusManager:
    """管理饱腹感、心情、状态衰减和 JSON 存档。"""

    def __init__(self, pet, save_path: Path):
        self.pet = pet
        self.save_path = save_path

        self.hunger = 100
        self.mood = 100
        self.load_status()

        self.status_timer = QTimer(self.pet)
        self.status_timer.timeout.connect(self.reduce_status)

    def start(self):
        """UI 创建完成后更新显示并启动状态计时器。"""
        self.update_ui()
        self.status_timer.start(60_000)

    def feed_pet(self):
        if self.hunger >= 100:
            self.pet.dialogue_manager.show_message("已经吃得饱饱的啦～")
            return

        self.hunger = min(100, self.hunger + 20)
        self.mood = min(100, self.mood + 3)

        self.update_ui()
        self.pet.dialogue_manager.show_message("好吃！饱腹感增加了 🍎")
        self.save_status()

    def touch_pet(self):
        self.increase_mood(
            amount=10,
            message="被摸摸了，好开心！✨",
        )

    def increase_mood(
        self,
        amount=10,
        message=None,
        show_message=True,
    ):
        """增加心情值，供按钮和头部摸摸互动共同调用。"""
        if self.mood >= 100:
            if show_message:
                self.pet.dialogue_manager.show_message(
                    "已经非常开心啦～"
                )
            return

        self.mood = min(100, self.mood + amount)
        self.update_ui()
        self.save_status()

        if show_message and message:
            self.pet.dialogue_manager.show_message(message)

    def reduce_status(self):
        self.hunger = max(0, self.hunger - 1)

        if self.hunger < 30:
            self.mood = max(0, self.mood - 2)
        else:
            self.mood = max(0, self.mood - 1)

        self.update_ui()
        self.save_status()

    def update_ui(self, temporary_message=None):
        """更新心情和饱腹进度条，不再显示状态文字。"""
        self.pet.hunger_bar.setValue(self.hunger)
        self.pet.mood_bar.setValue(self.mood)

        self.update_bar_style(
            self.pet.hunger_bar,
            self.hunger,
            "#ffb85c",
        )
        self.update_bar_style(
            self.pet.mood_bar,
            self.mood,
            "#ff8fa3",
        )

    @staticmethod
    def update_bar_style(progress_bar, value, normal_color):
        if value <= 20:
            chunk_color = "#ff6b6b"
        elif value <= 40:
            chunk_color = "#ffd166"
        else:
            chunk_color = normal_color

        progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                min-width: 135px;
                height: 14px;
                border: 1px solid #c8c8c8;
                border-radius: 7px;
                background-color: #eeeeee;
                text-align: center;
                color: #444444;
                font-size: 10px;
            }}

            QProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 6px;
            }}
            """
        )

    def load_status(self):
        if not self.save_path.exists():
            return

        try:
            with open(
                self.save_path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            self.hunger = max(
                0,
                min(100, int(data.get("hunger", 100))),
            )
            self.mood = max(
                0,
                min(100, int(data.get("mood", 100))),
            )

        except (
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            print(f"读取宠物状态失败：{error}")
            self.hunger = 100
            self.mood = 100

    def save_status(self):
        data = {
            "hunger": self.hunger,
            "mood": self.mood,
        }

        try:
            with open(
                self.save_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=4,
                )
        except OSError as error:
            print(f"保存宠物状态失败：{error}")
