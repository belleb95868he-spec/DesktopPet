import json
import time
from pathlib import Path

from PySide6.QtCore import QTimer

DEFAULT_COIN_COUNT = 30
DEFAULT_APPLE_COUNT = 3
APPLE_PRICE = 10
SHOP_PRICES = {
    "ice": 3,
    "sausage": 6,
    "apple": 10,
    "milk": 12,
    "bread": 20,
    "milktea": 25,
    "drink": 30,
    "ramen": 40,
    "salad": 45,
}


class StatusManager:
    """管理养成数值、金币、食物库存和 JSON 存档。"""

    def __init__(self, pet, save_path: Path):
        self.pet = pet
        self.save_path = save_path

        self.hunger = 100
        self.mood = 100
        self.coin_count = DEFAULT_COIN_COUNT
        self.apple_count = DEFAULT_APPLE_COUNT
        self.inventory = {
            item_id: 0
            for item_id in SHOP_PRICES
            if item_id != "apple"
        }
        self.companion_seconds = 0.0
        self.last_feed_amount = 0
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

    def feed_shop_item(self, item_id, hunger_amount, item_name):
        """Consume a dragged shop item and apply its hunger value."""
        self.last_feed_amount = 0
        if self.pet.is_economy_interaction_locked():
            return False
        if item_id not in SHOP_PRICES:
            return False
        if self.get_item_count(item_id) <= 0:
            self.pet.dialogue_manager.show_message(
                f"没有{item_name}了，先去商店购买吧。"
            )
            return False
        if self.hunger >= 100:
            self.pet.dialogue_manager.show_message("已经吃得饱饱的啦～")
            return False

        previous_hunger = self.hunger
        previous_mood = self.mood
        previous_count = self.get_item_count(item_id)
        try:
            if item_id == "apple":
                self.apple_count -= 1
            else:
                self.inventory[item_id] = previous_count - 1
            applied_amount = min(
                max(0, int(hunger_amount)),
                100 - self.hunger,
            )
            self.last_feed_amount = applied_amount
            self.hunger += applied_amount
            self.mood = min(100, self.mood + 5)
            self.pet.animation_manager.stop_hungry_after_feeding()
            self.update_ui()
            self.save_status()
            self.pet.dialogue_manager.show_message(
                f"吃掉了{item_name}，饱腹增加 {applied_amount}%"
            )
            return True
        except Exception as error:
            self.last_feed_amount = 0
            self.hunger = previous_hunger
            self.mood = previous_mood
            if item_id == "apple":
                self.apple_count = previous_count
            else:
                self.inventory[item_id] = previous_count
            self.update_ui()
            self.save_status()
            print(f"拖拽喂食失败，已回滚：{error}")
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
        return self.buy_item("apple", APPLE_PRICE)

    def buy_item(self, item_id, price=None):
        """Purchase any shop item and persist its inventory count."""
        if self.pet.is_economy_interaction_locked():
            return False
        if item_id not in SHOP_PRICES:
            return False
        item_price = SHOP_PRICES[item_id] if price is None else int(price)
        if not self.can_afford(item_price):
            self.pet.dialogue_manager.show_message(
                "金币不够，完成一次工作可以获得 10 金币。"
            )
            return False

        self.coin_count -= item_price
        if item_id == "apple":
            self.apple_count += 1
        else:
            self.inventory[item_id] = self.inventory.get(item_id, 0) + 1
        self.update_ui()
        self.save_status()
        return True

    def get_item_count(self, item_id):
        if item_id == "apple":
            return max(0, self.apple_count)
        return max(0, self.inventory.get(item_id, 0))

    def total_inventory_count(self):
        return sum(
            self.get_item_count(item_id)
            for item_id in SHOP_PRICES
        )

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
            saved_inventory = data.get("inventory", {})
            if isinstance(saved_inventory, dict):
                for item_id in self.inventory:
                    self.inventory[item_id] = self.safe_nonnegative_int(
                        saved_inventory.get(item_id, 0),
                        0,
                    )
                if "apple" in saved_inventory:
                    self.apple_count = self.safe_nonnegative_int(
                        saved_inventory.get("apple"),
                        self.apple_count,
                    )
            self.companion_seconds = self.safe_nonnegative_float(
                data.get("companion_seconds", 0),
                0.0,
            )
            cooldown_epoch = self.safe_nonnegative_float(
                data.get("work_cooldown_until_epoch", 0),
                0.0,
            )
            cooldown_remaining = max(0.0, cooldown_epoch - time.time())
            if cooldown_remaining > 0:
                self.pet.animation_manager.work_cooldown_until = (
                    time.monotonic() + cooldown_remaining
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
            self.inventory = {
                item_id: 0
                for item_id in SHOP_PRICES
                if item_id != "apple"
            }
            self.companion_seconds = 0.0

    @staticmethod
    def safe_nonnegative_int(value, default):
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def safe_nonnegative_float(value, default):
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return default

    def save_status(self):
        cooldown_remaining = max(
            0.0,
            self.pet.animation_manager.work_cooldown_until
            - time.monotonic(),
        )
        companionship = (
            self.pet.get_total_companion_seconds()
            if hasattr(self.pet, "get_total_companion_seconds")
            else self.companion_seconds
        )
        data = {
            "hunger": self.hunger,
            "mood": self.mood,
            "coin_count": max(0, self.coin_count),
            "apple_count": max(0, self.apple_count),
            "inventory": {
                item_id: self.get_item_count(item_id)
                for item_id in SHOP_PRICES
            },
            "companion_seconds": max(0.0, companionship),
            "work_cooldown_until_epoch": (
                time.time() + cooldown_remaining
                if cooldown_remaining > 0
                else 0
            ),
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
