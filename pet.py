import math
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QPixmap, QTransform, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from animation_manager import AnimationManager
from dialogue import DialogueManager
from hourly_greetings import HourlyGreetingManager
from petting_manager import PettingManager
from status_manager import APPLE_PRICE, StatusManager


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        self.pet_size = 250
        self.base_path = Path(__file__).resolve().parent
        self.save_path = self.base_path / "pet_status.json"

        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.drag_start_global = QPoint()
        self.window_start_position = QPoint()
        self.is_dragging = False
        self.work_window_drag = False
        self.petting_click_active = False
        self.lifted_pixmap = None
        self.drag_anchor_window = QPoint()
        self.drag_pivot = QPoint()
        self.drag_label_x = 0
        self.drag_swing_phase = 0.0
        self.drag_swing_amplitude = 5
        self.drag_swing_speed = 2.5
        self.drag_timer = QTimer(self)
        self.drag_timer.setInterval(16)
        self.drag_timer.timeout.connect(self.update_drag_swing)

        # ==================================================
        # 功能管理器
        # ==================================================

        self.animation_manager = AnimationManager(
            pet=self,
            base_path=self.base_path,
            pet_size=self.pet_size,
        )

        self.dialogue_manager = DialogueManager(
            self
        )

        self.status_manager = StatusManager(
            pet=self,
            save_path=self.save_path,
        )

        self.petting_manager = PettingManager(
            self
        )

        # 必须先创建 UI
        # 因为整点问候显示气泡时需要使用 pet_label
        self.setup_ui()

        # UI 创建完成后，再启动整点问候
        self.hourly_greeting_manager = HourlyGreetingManager(
            pet=self,
            dialogue_manager=self.dialogue_manager,
        )

        self.dialogue_manager.update_position()

        self.animation_manager.start()
        self.status_manager.start()

        self.show()

        # ==================================================
        # 临时测试整点问候
        # 取消下一行前面的 #，运行后会立即显示 14 点台词
        # 测试成功后记得重新加上 #
        # ==================================================

        # 已注释：仅用于调试，发布前请保持注释状态
        # self.hourly_greeting_manager.test_greeting(14)

    # ==================================================
    # UI
    # ==================================================

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)

        self.main_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        self.main_layout.setSpacing(5)

        self.main_layout.setAlignment(
            Qt.AlignCenter
        )

        self.pet_label = QLabel()

        self.pet_label.setAlignment(
            Qt.AlignCenter
        )

        self.pet_label.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.pet_label.setFixedSize(
            self.pet_size,
            self.pet_size,
        )

        self.pet_label.installEventFilter(
            self
        )

        if self.animation_manager.idle_frames:
            self.pet_label.setPixmap(
                self.animation_manager.idle_frames[0]
            )
        else:
            self.pet_label.setText(
                "没有找到 Idle 序列帧"
            )

            self.pet_label.setStyleSheet(
                """
                color: red;
                background: white;
                border-radius: 10px;
                """
            )

        self.main_layout.addWidget(
            self.pet_label,
            alignment=Qt.AlignCenter,
        )

        self.lifted_pixmap = self.load_lifted_pixmap()

        # ==================================================
        # 状态面板
        # ==================================================

        self.status_panel = QWidget()

        self.status_panel.setObjectName(
            "statusPanel"
        )

        panel_layout = QVBoxLayout(
            self.status_panel
        )

        panel_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        panel_layout.setSpacing(8)

        self.status_stack = QStackedWidget()
        panel_layout.addWidget(self.status_stack)

        # 主状态页面
        self.main_status_page = QWidget()
        main_status_layout = QVBoxLayout(self.main_status_page)
        main_status_layout.setContentsMargins(0, 0, 0, 0)
        main_status_layout.setSpacing(8)

        mood_layout = QHBoxLayout()

        self.mood_label = QLabel(
            "❤️ 心情"
        )

        self.mood_label.setFixedWidth(60)

        self.mood_bar = QProgressBar()

        self.mood_bar.setRange(
            0,
            100,
        )

        self.mood_bar.setTextVisible(
            True
        )

        self.mood_bar.setFormat(
            "%p%"
        )

        mood_layout.addWidget(
            self.mood_label
        )

        mood_layout.addWidget(
            self.mood_bar
        )

        hunger_layout = QHBoxLayout()

        self.hunger_label = QLabel(
            "🍖 饱腹"
        )

        self.hunger_label.setFixedWidth(60)

        self.hunger_bar = QProgressBar()

        self.hunger_bar.setRange(
            0,
            100,
        )

        self.hunger_bar.setTextVisible(
            True
        )

        self.hunger_bar.setFormat(
            "%p%"
        )

        hunger_layout.addWidget(
            self.hunger_label
        )

        hunger_layout.addWidget(
            self.hunger_bar
        )

        self.coin_label = QLabel()
        self.coin_label.setAlignment(Qt.AlignCenter)

        button_layout = QHBoxLayout()

        self.feed_button = QPushButton(
            "🍎 喂食"
        )

        self.shop_button = QPushButton(
            "🛒 商店"
        )

        self.feed_button.clicked.connect(
            self.open_food_page
        )

        self.shop_button.clicked.connect(
            self.open_shop_page
        )

        button_layout.addWidget(
            self.feed_button
        )

        button_layout.addWidget(self.shop_button)

        main_status_layout.addLayout(mood_layout)
        main_status_layout.addLayout(hunger_layout)
        main_status_layout.addWidget(self.coin_label)
        main_status_layout.addLayout(button_layout)
        self.status_stack.addWidget(self.main_status_page)

        # 商店页面
        self.shop_page = QWidget()
        shop_layout = QVBoxLayout(self.shop_page)
        shop_layout.setContentsMargins(0, 0, 0, 0)
        shop_layout.setSpacing(7)

        shop_title = QLabel("商店")
        shop_title.setAlignment(Qt.AlignCenter)
        self.shop_coin_label = QLabel()
        self.shop_coin_label.setAlignment(Qt.AlignCenter)
        shop_item_label = QLabel("🍎 苹果")
        shop_item_label.setAlignment(Qt.AlignCenter)
        shop_price_label = QLabel(f"价格：{APPLE_PRICE} 金币")
        shop_price_label.setAlignment(Qt.AlignCenter)
        self.shop_apple_count_label = QLabel()
        self.shop_apple_count_label.setAlignment(Qt.AlignCenter)
        self.shop_message_label = QLabel()
        self.shop_message_label.setAlignment(Qt.AlignCenter)
        self.buy_apple_button = QPushButton("购买")
        self.shop_back_button = QPushButton("返回")

        self.buy_apple_button.clicked.connect(
            self.buy_apple_from_shop
        )
        self.shop_back_button.clicked.connect(
            self.show_main_status_page
        )

        shop_layout.addWidget(shop_title)
        shop_layout.addWidget(self.shop_coin_label)
        shop_layout.addWidget(shop_item_label)
        shop_layout.addWidget(shop_price_label)
        shop_layout.addWidget(self.shop_apple_count_label)
        shop_layout.addWidget(self.shop_message_label)
        shop_layout.addWidget(self.buy_apple_button)
        shop_layout.addWidget(self.shop_back_button)
        self.status_stack.addWidget(self.shop_page)

        # 食物选择页面
        self.food_page = QWidget()
        food_layout = QVBoxLayout(self.food_page)
        food_layout.setContentsMargins(0, 0, 0, 0)
        food_layout.setSpacing(7)

        food_title = QLabel("选择食物")
        food_title.setAlignment(Qt.AlignCenter)
        food_item_label = QLabel("🍎 苹果")
        food_item_label.setAlignment(Qt.AlignCenter)
        self.food_apple_count_label = QLabel()
        self.food_apple_count_label.setAlignment(Qt.AlignCenter)
        self.food_message_label = QLabel()
        self.food_message_label.setAlignment(Qt.AlignCenter)
        self.feed_apple_button = QPushButton("喂食")
        self.food_back_button = QPushButton("返回")

        self.feed_apple_button.clicked.connect(
            self.feed_apple_from_food
        )
        self.food_back_button.clicked.connect(
            self.show_main_status_page
        )

        food_layout.addWidget(food_title)
        food_layout.addWidget(food_item_label)
        food_layout.addWidget(self.food_apple_count_label)
        food_layout.addWidget(self.food_message_label)
        food_layout.addWidget(self.feed_apple_button)
        food_layout.addWidget(self.food_back_button)
        self.status_stack.addWidget(self.food_page)
        self.status_stack.setCurrentWidget(self.main_status_page)
        self.status_stack.setFixedHeight(
            max(
                self.main_status_page.sizeHint().height(),
                self.shop_page.sizeHint().height(),
                self.food_page.sizeHint().height(),
            )
        )

        self.main_layout.addWidget(
            self.status_panel
        )

        self.status_panel.hide()

        self.setStyleSheet(
            """
            QWidget#statusPanel {
                background-color: rgba(255, 255, 255, 235);
                border: 1px solid rgba(120, 120, 120, 100);
                border-radius: 14px;
            }

            QLabel {
                color: #444444;
                font-size: 13px;
            }

            QProgressBar {
                min-width: 135px;
                height: 14px;
                border: 1px solid #c8c8c8;
                border-radius: 7px;
                background-color: #eeeeee;
                text-align: center;
                color: #444444;
                font-size: 10px;
            }

            QPushButton {
                min-height: 30px;
                padding-left: 12px;
                padding-right: 12px;
                background-color: white;
                color: #444444;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                font-size: 13px;
            }

            QPushButton:hover {
                background-color: #fff4df;
                border-color: #efb45f;
            }

            QPushButton:pressed {
                background-color: #ffe5b9;
            }
            """
        )

        self.adjustSize()
        self.update_drag_anchor_window()

    # ==================================================
    # 鼠标与菜单
    # ==================================================

    def eventFilter(
        self,
        watched,
        event,
    ):
        if watched is self.pet_label:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.petting_click_active = (
                        self.animation_manager.is_petting()
                    )
                    self.drag_start_global = (
                        event.globalPosition().toPoint()
                    )

                    self.window_start_position = (
                        self.pos()
                    )

                    self.is_dragging = False
                    self.work_window_drag = (
                        self.animation_manager.current_state == "work"
                    )

                    event.accept()

                    return True

                if event.button() == Qt.RightButton:
                    self.show_context_menu(
                        event.globalPosition().toPoint()
                    )

                    event.accept()

                    return True

            elif event.type() == QEvent.MouseMove:
                if event.buttons() & Qt.LeftButton:
                    if self.petting_click_active:
                        event.accept()
                        return True

                    current_global = (
                        event.globalPosition().toPoint()
                    )

                    movement = (
                        current_global
                        - self.drag_start_global
                    )

                    if movement.manhattanLength() > 5:
                        if not self.is_dragging:
                            self.is_dragging = True
                            if not self.work_window_drag:
                                self.start_drag()

                    if self.is_dragging:
                        self.current_drag_global = current_global
                        if self.work_window_drag:
                            self.move(
                                self.window_start_position
                                + movement
                            )
                        else:
                            self.move_drag_anchor_to_mouse(
                                self.current_drag_global
                            )
                            if not self.drag_timer.isActive():
                                self.drag_timer.start()
                            if hasattr(self, "activity_trigger_manager"):
                                self.activity_trigger_manager._register_drag_motion()

                    event.accept()

                    return True

            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if self.petting_click_active:
                        local_position = event.position().toPoint()
                        if self.petting_manager.is_head_position(
                            local_position
                        ):
                            self.petting_manager.register_head_click()
                        else:
                            self.toggle_status_panel()
                        self.petting_click_active = False
                        self.is_dragging = False
                        event.accept()
                        return True

                    if self.work_window_drag:
                        if not self.is_dragging:
                            local_position = (
                                event.position().toPoint()
                            )
                            if self.petting_manager.is_head_position(
                                local_position
                            ):
                                self.dialogue_manager.show_message(
                                    "等等，我先看完这个文件",
                                    duration=3500,
                                    allow_during_work=True,
                                )
                        self.is_dragging = False
                        self.work_window_drag = False
                        event.accept()
                        return True

                    if self.is_dragging:
                        self.drag_timer.stop()
                        self.drag_swing_phase = 0.0
                        self.move_drag_anchor_to_mouse(
                            self.current_drag_global
                        )
                        self.stop_drag()
                    else:
                        local_position = (
                            event.position().toPoint()
                        )

                        if self.petting_manager.is_head_position(
                            local_position
                        ):
                            self.petting_manager.register_head_click()
                        else:
                            self.toggle_status_panel()

                    self.is_dragging = False
                    self.work_window_drag = False

                    event.accept()

                    return True

        return super().eventFilter(
            watched,
            event,
        )

    def start_drag(self):
        if self.is_interaction_locked():
            return
        self.animation_manager.pause_for_drag()
        if self.lifted_pixmap is not None:
            rotated = self.render_rotated_lifted_pixmap(0.0)
            self.pet_label.setPixmap(rotated)
            self.pet_label.update()

    def stop_drag(self):
        if self.is_interaction_locked():
            return
        self.animation_manager.resume_idle()

    def update_drag_swing(self):
        if (
            not self.is_dragging
            or self.is_interaction_locked()
        ):
            self.drag_timer.stop()
            return

        self.drag_swing_phase += (
            self.drag_swing_speed
            * self.drag_timer.interval()
            / 1000.0
        )
        angle = (
            self.drag_swing_amplitude
            * math.sin(self.drag_swing_phase)
        )
        if self.lifted_pixmap is not None:
            rotated = self.render_rotated_lifted_pixmap(angle)
            self.pet_label.setPixmap(rotated)
            self.pet_label.update()

    def render_rotated_lifted_pixmap(self, angle: float):
        if self.lifted_pixmap is None:
            return self.animation_manager.idle_frames[0]

        canvas = QPixmap(self.pet_size, self.pet_size)
        canvas.fill(Qt.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        transform = QTransform()
        transform.translate(
            self.drag_pivot.x(),
            self.drag_pivot.y(),
        )
        transform.rotate(angle)
        transform.translate(
            -self.drag_pivot.x(),
            -self.drag_pivot.y(),
        )
        painter.setTransform(transform)
        painter.drawPixmap(self.drag_label_x, 0, self.lifted_pixmap)
        painter.end()

        return canvas

    def load_lifted_pixmap(self):
        lifted_path = self.base_path / "assets" / "lifted" / "lifted.png"
        pixmap = QPixmap(str(lifted_path))
        if pixmap.isNull():
            print(f"无法读取 lifted 图像：{lifted_path}")
            return None

        scaled = pixmap.scaled(
            self.pet_size,
            self.pet_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        pivot = QPoint(
            round(scaled.width() * 603 / pixmap.width()),
            round(scaled.height() * 150 / pixmap.height()),
        )
        self.drag_label_x = (
            self.pet_size - scaled.width()
        ) // 2
        self.drag_pivot = QPoint(
            self.drag_label_x + pivot.x(),
            pivot.y(),
        )
        self.update_drag_anchor_window()

        return scaled

    def update_drag_anchor_window(self):
        if not hasattr(self, "pet_label"):
            return
        label_pos = self.pet_label.pos()
        self.drag_anchor_window = QPoint(
            label_pos.x() + self.drag_pivot.x(),
            label_pos.y() + self.drag_pivot.y(),
        )

    def move_drag_anchor_to_mouse(self, mouse_global_position):
        """按红点当前的真实屏幕坐标移动窗口，使其与鼠标重合。"""
        anchor_global_position = self.pet_label.mapToGlobal(
            self.drag_pivot
        )
        self.move(
            self.pos()
            + mouse_global_position
            - anchor_global_position
        )

    def refresh_economy_ui(self):
        """统一刷新主状态、商店和食物页面的金币与库存。"""
        manager = self.status_manager
        coin_count = max(0, manager.coin_count)
        apple_count = max(0, manager.apple_count)
        interaction_enabled = not self.is_economy_interaction_locked()

        self.coin_label.setText(f"🪙 × {coin_count}")
        self.shop_coin_label.setText(f"金币：{coin_count}")
        self.shop_apple_count_label.setText(f"持有：{apple_count}")
        self.food_apple_count_label.setText(f"持有：{apple_count}")

        self.feed_button.setEnabled(interaction_enabled)
        self.shop_button.setEnabled(interaction_enabled)
        self.buy_apple_button.setEnabled(
            interaction_enabled
            and manager.can_afford(APPLE_PRICE)
        )
        self.feed_apple_button.setEnabled(
            interaction_enabled
            and apple_count > 0
            and manager.hunger < 100
        )

        if coin_count < APPLE_PRICE:
            self.shop_message_label.setText("金币不足")
        elif self.shop_message_label.text() == "金币不足":
            self.shop_message_label.clear()

        if apple_count == 0:
            self.food_message_label.setText(
                "没有苹果了，去商店买一个吧。"
            )
        elif manager.hunger >= 100:
            self.food_message_label.setText("已经吃得饱饱的啦～")
        elif self.food_message_label.text() in (
            "没有苹果了，去商店买一个吧。",
            "已经吃得饱饱的啦～",
        ):
            self.food_message_label.clear()

    def open_shop_page(self):
        if self.is_economy_interaction_locked():
            return
        self.shop_message_label.clear()
        self.refresh_economy_ui()
        self.status_stack.setCurrentWidget(self.shop_page)

    def open_food_page(self):
        if self.is_economy_interaction_locked():
            return
        self.food_message_label.clear()
        self.refresh_economy_ui()
        self.status_stack.setCurrentWidget(self.food_page)

    def show_main_status_page(self):
        if self.is_economy_interaction_locked():
            return
        self.refresh_economy_ui()
        self.status_stack.setCurrentWidget(self.main_status_page)

    def buy_apple_from_shop(self):
        if self.is_economy_interaction_locked():
            return
        purchase_succeeded = self.status_manager.buy_apple()
        self.refresh_economy_ui()
        self.shop_message_label.setText(
            "购买成功" if purchase_succeeded else "金币不足"
        )

    def feed_apple_from_food(self):
        if self.is_economy_interaction_locked():
            return
        feeding_succeeded = self.status_manager.feed_with_apple()
        self.refresh_economy_ui()
        if feeding_succeeded:
            self.food_message_label.setText("喂食成功")
        elif self.status_manager.apple_count <= 0:
            self.food_message_label.setText(
                "没有苹果了，去商店买一个吧。"
            )
        elif self.status_manager.hunger >= 100:
            self.food_message_label.setText("已经吃得饱饱的啦～")

    def collapse_status_panel_for_work(self):
        """进入 work 时收起状态栏，不触发普通交互逻辑。"""
        if not self.status_panel.isVisible():
            return
        self.status_panel.hide()
        self.status_stack.setCurrentWidget(self.main_status_page)
        self.adjustSize()
        self.dialogue_manager.update_position()
        self.keep_inside_screen()

    def toggle_status_panel(self):
        if self.is_economy_interaction_locked():
            return
        if self.status_panel.isVisible():
            self.status_panel.hide()
        else:
            self.show_main_status_page()
            self.status_panel.show()

        self.adjustSize()

        self.dialogue_manager.update_position()

        self.keep_inside_screen()

    def is_interaction_locked(self):
        return self.animation_manager.is_interaction_locked()

    def is_economy_interaction_locked(self):
        """工作状态锁定商店和喂食；摸头动画期间保持可操作。"""
        return self.animation_manager.current_state == "work"

    def show_context_menu(
        self,
        global_position,
    ):
        menu = QMenu(self)

        toggle_action = QAction(
            "显示／隐藏状态",
            self,
        )

        toggle_action.triggered.connect(
            self.toggle_status_panel
        )

        quit_action = QAction(
            "退出桌宠",
            self,
        )

        quit_action.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            toggle_action
        )

        menu.addSeparator()

        menu.addAction(
            quit_action
        )

        menu.exec(
            global_position
        )

    # ==================================================
    # 屏幕边界与关闭
    # ==================================================

    def keep_inside_screen(self):
        screen = QGuiApplication.screenAt(
            self.frameGeometry().center()
        )

        if screen is None:
            screen = QGuiApplication.primaryScreen()

        available = screen.availableGeometry()

        new_x = min(
            max(
                self.x(),
                available.left(),
            ),
            available.right()
            - self.width()
            + 1,
        )

        new_y = min(
            max(
                self.y(),
                available.top(),
            ),
            available.bottom()
            - self.height()
            + 1,
        )

        self.move(
            new_x,
            new_y,
        )

    def closeEvent(
        self,
        event,
    ):
        self.status_manager.save_status()

        event.accept()


def run():
    app = QApplication(
        sys.argv
    )

    pet = DesktopPet()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    run()
