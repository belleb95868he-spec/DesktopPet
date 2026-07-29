import json
from pathlib import Path

from PySide6.QtCore import QTimer

DEFAULT_COIN_COUNT = 30
DEFAULT_APPLE_COUNT = 3
APPLE_PRICE = 3


class StatusManager:
    """管理养成数值、金币、食物库存和 JSON 存档。"""

    def __init__(self, pet, save_path: Path):
        self.pet = pet
        self.save_path = save_path

        self.hunger = 100
        self.mood = 100
        self.coin_count = DEFAULT_COIN_COUNT
        self.apple_count = DEFAULT_APPLE_COUNT
        self.load_status()

        self.status_timer = QTimer(self.pet)
        self.status_timer.timeout.connect(self.reduce_status)

    def start(self):
        """UI 创建完成后更新显示并启动状态计时器。"""
        self.update_ui()
        self.status_timer.start(60_000)

    def feed_pet(self, save=True):
        """执行原有喂食效果；库存入口应调用 feed_with_apple。"""
        if self.pet.is_economy_interaction_locked():
            return False
        if self.hunger >= 100:
            self.pet.dialogue_manager.show_message("已经吃得饱饱的啦～")
            return False

        self.hunger = min(100, self.hunger + 10)
        self.mood = min(100, self.mood + 5)

        self.update_ui()
        self.pet.dialogue_manager.show_message("好吃！饱腹感增加了 10% 🍎")
        if save:
            self.save_status()
        return True

    def feed_with_apple(self):
        """消费一个苹果后复用原有喂食逻辑，失败时回滚数值。"""
        if self.pet.is_economy_interaction_locked():
            return False
        if self.apple_count <= 0:
            self.pet.dialogue_manager.show_message(
                "没有苹果了，去商店买一个吧。"
            )
            return False
        if self.hunger >= 100:
            self.pet.dialogue_manager.show_message("已经吃得饱饱的啦～")
            return False

        previous_values = (
            self.apple_count,
            self.hunger,
            self.mood,
        )
        try:
            self.apple_count -= 1
            if not self.feed_pet(save=False):
                self.apple_count, self.hunger, self.mood = previous_values
                self.update_ui()
                return False
            self.pet.animation_manager.stop_hungry_after_feeding()
            self.update_ui()
            self.save_status()
            return True
        except Exception as error:
            self.apple_count, self.hunger, self.mood = previous_values
            self.update_ui()
            self.save_status()
            print(f"喂食苹果失败，已回滚：{error}")
            return False

    def touch_pet(self):
        if self.pet.is_interaction_locked():
            return
        self.increase_mood(
            amount=10,
            message="被摸摸了，好开心！✨",
        )

    def increase_mood(
        self,
        amount=10,
        message=None,
        show_message=True,
        allow_during_petting=False,
    ):
        """增加心情值，供按钮和头部摸摸互动共同调用。"""
        current_state = self.pet.animation_manager.current_state
        if current_state == "work":
            return
        if current_state == "petting" and not allow_during_petting:
            return
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

    def add_coins(self, amount):
        amount = int(amount)
        if amount <= 0:
            return False
        self.coin_count = max(0, self.coin_count + amount)
        self.update_ui()
        self.save_status()
        return True

    def can_afford(self, amount):
        return amount > 0 and self.coin_count >= amount

    def spend_coins(self, amount):
        amount = int(amount)
        if not self.can_afford(amount):
            return False
        self.coin_count -= amount
        self.update_ui()
        self.save_status()
        return True

    def add_apples(self, amount):
        amount = int(amount)
        if amount <= 0:
            return False
        self.apple_count = max(0, self.apple_count + amount)
        self.update_ui()
        self.save_status()
        return True

    def has_apple(self):
        return self.apple_count > 0

    def consume_apple(self):
        if not self.has_apple():
            return False
        self.apple_count -= 1
        self.update_ui()
        self.save_status()
        return True

    def buy_apple(self):
        """一次性完成扣金币和增加库存，避免半笔交易。"""
        if self.pet.is_economy_interaction_locked():
            return False
        if not self.can_afford(APPLE_PRICE):
            self.pet.dialogue_manager.show_message(
                "金币不够，完成一次工作可以获得 10 金币。"
            )
            return False

        self.coin_count -= APPLE_PRICE
        self.apple_count += 1
        self.update_ui()
        self.save_status()
        self.pet.dialogue_manager.show_message("获得了 1 个苹果 🍎")
        return True

    def reduce_status(self):
        self.hunger = max(0, self.hunger - 1)

        if self.hunger < 30:
            self.mood = max(0, self.mood - 2)
        else:
            self.mood = max(0, self.mood - 1)

        self.update_ui()
        self.save_status()

    def update_ui(self, temporary_message=None):
        """统一刷新状态条及金币、库存相关页面。"""
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
        if hasattr(self.pet, "refresh_economy_ui"):
            self.pet.refresh_economy_ui()

    @staticmethod
    def update_bar_style(progress_bar, value, normal_color):
        if progress_bar.property("profileBar"):
            progress_bar.update()
            return

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

            if not isinstance(data, dict):
                raise ValueError("存档根节点必须是对象")

            self.hunger = max(
                0,
                min(100, int(data.get("hunger", 100))),
            )
            self.mood = max(
                0,
                min(100, int(data.get("mood", 100))),
            )
            self.coin_count = self.safe_nonnegative_int(
                data.get("coin_count", DEFAULT_COIN_COUNT),
                DEFAULT_COIN_COUNT,
            )
            self.apple_count = self.safe_nonnegative_int(
                data.get("apple_count", DEFAULT_APPLE_COUNT),
                DEFAULT_APPLE_COUNT,
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
            self.coin_count = DEFAULT_COIN_COUNT
            self.apple_count = DEFAULT_APPLE_COUNT

    @staticmethod
    def safe_nonnegative_int(value, default):
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return default

    def save_status(self):
        data = {
            "hunger": self.hunger,
            "mood": self.mood,
            "coin_count": max(0, self.coin_count),
            "apple_count": max(0, self.apple_count),
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
