import json
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from animation_manager import AnimationManager


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        # =========================
        # 基础设置
        # =========================

        self.pet_size = 250
        self.base_path = Path(__file__).resolve().parent
        self.save_path = self.base_path / "pet_status.json"

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 鼠标拖动
        self.drag_start_global = QPoint()
        self.window_start_position = QPoint()
        self.is_dragging = False

        # 宠物数值
        self.hunger = 100
        self.mood = 100
        self.load_status()

        # 动画全部交给 AnimationManager 管理
        self.animation_manager = AnimationManager(
            pet=self,
            base_path=self.base_path,
            pet_size=self.pet_size,
        )

        # 创建 UI
        self.setup_ui()

        # UI 创建完成后再启动动画
        self.animation_manager.start()

        # 状态计时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.reduce_status)
        self.status_timer.start(60_000)

        self.show()

    # ==================================================
    # UI
    # ==================================================

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(5)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # 宠物动画显示区域
        self.pet_label = QLabel()
        self.pet_label.setAlignment(Qt.AlignCenter)
        self.pet_label.setAttribute(Qt.WA_TranslucentBackground)
        self.pet_label.setFixedSize(self.pet_size, self.pet_size)
        self.pet_label.installEventFilter(self)

        if self.animation_manager.idle_frames:
            self.pet_label.setPixmap(
                self.animation_manager.idle_frames[0]
            )
        else:
            self.pet_label.setText("没有找到 Idle 序列帧")
            self.pet_label.setStyleSheet(
                "color: red; background: white; border-radius: 10px;"
            )

        self.main_layout.addWidget(
            self.pet_label,
            alignment=Qt.AlignCenter
        )

        # 状态面板
        self.status_panel = QWidget()
        self.status_panel.setObjectName("statusPanel")

        panel_layout = QVBoxLayout(self.status_panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(8)

        # 心情条
        mood_layout = QHBoxLayout()
        self.mood_label = QLabel("❤️ 心情")
        self.mood_label.setFixedWidth(60)

        self.mood_bar = QProgressBar()
        self.mood_bar.setRange(0, 100)
        self.mood_bar.setTextVisible(True)
        self.mood_bar.setFormat("%p%")

        mood_layout.addWidget(self.mood_label)
        mood_layout.addWidget(self.mood_bar)

        # 饱腹条
        hunger_layout = QHBoxLayout()
        self.hunger_label = QLabel("🍖 饱腹")
        self.hunger_label.setFixedWidth(60)

        self.hunger_bar = QProgressBar()
        self.hunger_bar.setRange(0, 100)
        self.hunger_bar.setTextVisible(True)
        self.hunger_bar.setFormat("%p%")

        hunger_layout.addWidget(self.hunger_label)
        hunger_layout.addWidget(self.hunger_bar)

        # 提示文字
        self.message_label = QLabel("状态很好～")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)

        # 按钮
        button_layout = QHBoxLayout()
        self.feed_button = QPushButton("🍎 喂食")
        self.touch_button = QPushButton("🤲 摸摸")

        self.feed_button.clicked.connect(self.feed_pet)
        self.touch_button.clicked.connect(self.touch_pet)

        button_layout.addWidget(self.feed_button)
        button_layout.addWidget(self.touch_button)

        panel_layout.addLayout(mood_layout)
        panel_layout.addLayout(hunger_layout)
        panel_layout.addWidget(self.message_label)
        panel_layout.addLayout(button_layout)

        self.main_layout.addWidget(self.status_panel)
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

        self.update_status_ui()
        self.adjustSize()

    def eventFilter(self, watched, event):
        """区分单击、拖动和右键菜单。"""
        if watched is self.pet_label:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_start_global = event.globalPosition().toPoint()
                    self.window_start_position = self.pos()
                    self.is_dragging = False
                    event.accept()
                    return True

                if event.button() == Qt.RightButton:
                    self.show_context_menu(event.globalPosition().toPoint())
                    event.accept()
                    return True

            elif event.type() == QEvent.MouseMove:
                if event.buttons() & Qt.LeftButton:
                    current_global = event.globalPosition().toPoint()
                    movement = current_global - self.drag_start_global

                    if movement.manhattanLength() > 5:
                        self.is_dragging = True

                    if self.is_dragging:
                        self.move(self.window_start_position + movement)

                    event.accept()
                    return True

            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if not self.is_dragging:
                        self.toggle_status_panel()

                    self.is_dragging = False
                    event.accept()
                    return True

        return super().eventFilter(watched, event)

    def toggle_status_panel(self):
        """单击人物显示或隐藏状态面板。"""
        if self.status_panel.isVisible():
            self.status_panel.hide()
        else:
            self.status_panel.show()

        self.adjustSize()
        self.keep_inside_screen()

    def show_context_menu(self, global_position):
        menu = QMenu(self)

        toggle_action = QAction("显示／隐藏状态", self)
        toggle_action.triggered.connect(self.toggle_status_panel)

        quit_action = QAction("退出桌宠", self)
        quit_action.triggered.connect(QApplication.quit)

        menu.addAction(toggle_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.exec(global_position)

    # ==================================================
    # 状态系统
    # ==================================================

    def feed_pet(self):
        if self.hunger >= 100:
            self.message_label.setText("已经吃得饱饱的啦～")
            return

        self.hunger = min(100, self.hunger + 20)
        self.mood = min(100, self.mood + 3)

        self.update_status_ui("好吃！饱腹感增加了 🍎")
        self.save_status()

    def touch_pet(self):
        if self.mood >= 100:
            self.message_label.setText("已经非常开心啦～")
            return

        self.mood = min(100, self.mood + 10)

        self.update_status_ui("被摸摸了，好开心！✨")
        self.save_status()

    def reduce_status(self):
        self.hunger = max(0, self.hunger - 1)

        if self.hunger < 30:
            self.mood = max(0, self.mood - 2)
        else:
            self.mood = max(0, self.mood - 1)

        self.update_status_ui()
        self.save_status()

    def update_status_ui(self, temporary_message=None):
        self.hunger_bar.setValue(self.hunger)
        self.mood_bar.setValue(self.mood)

        if temporary_message:
            self.message_label.setText(temporary_message)
        elif self.hunger <= 10:
            self.message_label.setText("肚子好饿……快喂喂我吧 🥺")
        elif self.hunger <= 30:
            self.message_label.setText("有一点饿了……")
        elif self.mood <= 10:
            self.message_label.setText("心情不太好，想被摸摸……")
        elif self.mood <= 30:
            self.message_label.setText("今天有一点没精神。")
        else:
            self.message_label.setText("状态很好～")

        self.update_bar_style(
            self.hunger_bar,
            self.hunger,
            "#ffb85c"
        )
        self.update_bar_style(
            self.mood_bar,
            self.mood,
            "#ff8fa3"
        )

    def update_bar_style(self, progress_bar, value, normal_color):
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
            with open(self.save_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.hunger = max(
                0,
                min(100, int(data.get("hunger", 100)))
            )
            self.mood = max(
                0,
                min(100, int(data.get("mood", 100)))
            )

        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            print(f"读取宠物状态失败：{error}")
            self.hunger = 100
            self.mood = 100

    def save_status(self):
        data = {
            "hunger": self.hunger,
            "mood": self.mood,
        }

        try:
            with open(self.save_path, "w", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=4
                )
        except OSError as error:
            print(f"保存宠物状态失败：{error}")

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
            max(self.x(), available.left()),
            available.right() - self.width() + 1
        )

        new_y = min(
            max(self.y(), available.top()),
            available.bottom() - self.height() + 1
        )

        self.move(new_x, new_y)

    def closeEvent(self, event):
        self.save_status()
        event.accept()


def run():
    app = QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()