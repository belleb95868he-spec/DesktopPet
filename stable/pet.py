import json
import random
import re
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QEvent, Qt, QTimer
from PySide6.QtGui import QAction, QGuiApplication, QPixmap, QTransform
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

        # 当前动画状态：idle / blink / walk / sing
        self.current_state = "idle"

        # 等待在 Idle 边界切换动作
        self.wait_blink = False
        self.wait_walk = False
        self.wait_sing = False

        # 记录上一个真正播放完成的动作，防止连续 Sing
        self.last_action = "idle"

        # 宠物数值
        self.hunger = 100
        self.mood = 100
        self.load_status()

        # =========================
        # 读取序列帧
        # =========================

        self.idle_frames = self.load_animation_frames(
            self.base_path / "assets" / "idle",
            "idle_*.png"
        )

        self.blink_frames = self.load_animation_frames(
            self.base_path / "assets" / "blink",
            "blink_*.png"
        )

        self.sing_frames = self.load_animation_frames(
            self.base_path / "assets" / "sing",
            "sing_*.png"
        )

        # 原始 Walk 素材朝屏幕左边
        self.walk_frames_left = self.load_animation_frames(
            self.base_path / "assets" / "walk",
            "walk_*.png"
        )

        # 提前生成朝右的帧，避免播放时每帧临时翻转而卡顿
        self.walk_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation
            )
            for frame in self.walk_frames_left
        ]

        # 保留兼容变量
        self.walk_frames = self.walk_frames_left

        self.idle_index = 0
        self.blink_index = 0
        self.walk_index = 0
        self.sing_index = 0

        print(f"Idle 帧数：{len(self.idle_frames)}")
        print(f"Blink 帧数：{len(self.blink_frames)}")
        print(f"Walk 帧数：{len(self.walk_frames)}")
        print(f"Sing 帧数：{len(self.sing_frames)}")

        # =========================
        # 创建 UI
        # =========================

        self.setup_ui()

        # =========================
        # Idle 计时器
        # =========================

        self.idle_interval = 70

        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.play_idle_frame)
        self.idle_timer.start(self.idle_interval)

        # =========================
        # Blink 计时器
        # =========================

        self.blink_interval = 80

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.play_blink_frame)


        # =========================
        # Walk 计时器
        # =========================

        # Walk 动画按约 30 fps 播放
        self.walk_interval = 33

        self.walk_timer = QTimer(self)
        self.walk_timer.setTimerType(Qt.PreciseTimer)
        self.walk_timer.timeout.connect(self.play_walk_frame)

        # 每完整播放一轮 Walk 动画，窗口移动的总距离。
        # 滑步时只需要微调这个数：脚向后滑就减小，身体像踏步不前就增大。
        self.walk_distance_per_cycle = 95.0
        self.walk_move_per_frame = (
            self.walk_distance_per_cycle / max(1, len(self.walk_frames))
        )
        self.walk_position_x = float(self.x())


        # 1 为向右，-1 为向左
        self.walk_direction = 1
        self.walk_steps_remaining = 0

        # =========================
        # Sing 计时器
        # =========================

        self.sing_interval = 50

        self.sing_timer = QTimer(self)
        self.sing_timer.setTimerType(Qt.PreciseTimer)
        self.sing_timer.timeout.connect(self.play_sing_frame)

        # =========================
        # 统一随机动作计时器
        # =========================

        self.action_timer = QTimer(self)
        self.action_timer.setSingleShot(True)
        self.action_timer.timeout.connect(self.choose_next_action)

        # =========================
        # 状态计时器
        # =========================

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.reduce_status)
        self.status_timer.start(60_000)

        # =========================
        # 安排随机动作
        # =========================

        self.schedule_next_action()

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

        if self.idle_frames:
            self.pet_label.setPixmap(self.idle_frames[0])
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
    # 图片读取
    # ==================================================

    def get_frame_number(self, image_path):
        numbers = re.findall(r"\d+", image_path.stem)
        return int(numbers[-1]) if numbers else 0

    def load_image(self, image_path):
        pixmap = QPixmap(str(image_path))

        if pixmap.isNull():
            return None

        return pixmap.scaled(
            self.pet_size,
            self.pet_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

    def load_animation_frames(self, folder, filename_pattern):
        frames = []

        if not folder.exists():
            print(f"文件夹不存在：{folder}")
            return frames

        files = sorted(
            folder.glob(filename_pattern),
            key=self.get_frame_number
        )

        for image_path in files:
            frame = self.load_image(image_path)

            if frame is None:
                print(f"无法读取图片：{image_path}")
            else:
                frames.append(frame)

        return frames

    def get_walk_frame(self):
        """原始素材朝左；向右时使用预先水平翻转好的序列帧。"""
        if self.walk_direction == 1:
            return self.walk_frames_right[self.walk_index]

        return self.walk_frames_left[self.walk_index]

    # ==================================================
    # 统一随机动作调度器
    # ==================================================

    def schedule_next_action(self):
        """2～5 秒后随机抽取下一动作。"""
        if self.current_state != "idle":
            return

        self.action_timer.start(
            random.randint(2000, 5000)
        )

    def choose_next_action(self):
        """
        40% Idle
        20% Blink
        30% Walk
        10% Sing

        抽到动作后立即播放，不再等待 Idle 首帧或尾帧。
        """
        if self.current_state != "idle":
            return

        roll = random.randint(1, 100)
        print(f"随机动作点数：{roll}")

        if roll <= 40:
            # 40%：继续 Idle
            print("本次动作：Idle")

            # Idle 已经把两次 Sing 隔开，
            # 所以下一次允许再次抽到 Sing
            self.last_action = "idle"

            self.schedule_next_action()
            return

        if roll <= 60:
            # 20%：Blink
            if self.blink_frames:
                print("本次动作：Blink")
                self.start_blink()
            else:
                self.schedule_next_action()
            return

        if roll <= 90:
            # 30%：Walk
            if self.walk_frames:
                print("本次动作：Walk")
                self.start_walk()
            else:
                self.schedule_next_action()
            return

        # 10%：Sing
        if self.last_action == "sing":
            # 不能连续唱两次，本次继续 Idle
            print("Sing 被跳过：上一个动作也是 Sing")
            self.schedule_next_action()
            return

        if self.sing_frames:
            print("本次动作：Sing")
            self.start_sing()
        else:
            self.schedule_next_action()

    # ==================================================
    # Idle
    # ==================================================

    def play_idle_frame(self):
        if self.current_state != "idle" or not self.idle_frames:
            return

        self.pet_label.setPixmap(
            self.idle_frames[self.idle_index]
        )

        self.idle_index = (
            self.idle_index + 1
        ) % len(self.idle_frames)

    # ==================================================
    # Blink
    # ==================================================

    def start_blink(self):
        if not self.blink_frames:
            self.schedule_next_action()
            return

        self.current_state = "blink"
        self.blink_index = 0

        self.wait_blink = False
        self.wait_walk = False
        self.wait_sing = False

        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.start(self.blink_interval)

    def play_blink_frame(self):
        if self.current_state != "blink":
            return

        if self.blink_index < len(self.blink_frames):
            self.pet_label.setPixmap(
                self.blink_frames[self.blink_index]
            )
            self.blink_index += 1
            return

        self.blink_timer.stop()

        self.current_state = "idle"
        self.last_action = "blink"
        self.idle_index = 0
        self.blink_index = 0

        if self.idle_frames:
            self.pet_label.setPixmap(self.idle_frames[0])

        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

    # ==================================================
    # Walk
    # ==================================================

    def start_walk(self):
        if not self.walk_frames:
            return

        self.current_state = "walk"
        self.walk_index = 0

        self.wait_walk = False
        self.wait_blink = False
        self.wait_sing = False

        self.action_timer.stop()
        self.idle_timer.stop()

        self.walk_direction = random.choice([-1, 1])
        self.walk_loops_remaining = random.randint(1, 2)
        self.walk_position_x = float(self.x())

        self.walk_timer.start(self.walk_interval)

    def play_walk_frame(self):
        if self.current_state != "walk" or not self.walk_frames:
            return

        # 显示当前方向的 Walk 帧
        self.pet_label.setPixmap(self.get_walk_frame())

        # 当前帧播放时同步移动
        self.move_pet_one_frame()

        self.walk_index += 1

        # 只有完整播放完全部 Walk 帧，才算完成一轮
        if self.walk_index >= len(self.walk_frames):
            self.walk_index = 0
            self.walk_loops_remaining -= 1

            # 所有轮数播放完后，立即停止移动并回到 Idle
            if self.walk_loops_remaining <= 0:
                self.stop_walk()
                return

    def move_pet_one_frame(self):
        if self.current_state != "walk" or self.is_dragging:
            return

        screen = QGuiApplication.screenAt(
            self.frameGeometry().center()
        )
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        available = screen.availableGeometry()
        left_limit = available.left()
        right_limit = available.right() - self.width() + 1

        self.walk_position_x += (
            self.walk_move_per_frame * self.walk_direction
        )

        # 碰到边缘就改变方向，同时改用对应方向的图片
        if self.walk_position_x <= left_limit:
            self.walk_position_x = float(left_limit)
            self.walk_direction = 1

        elif self.walk_position_x >= right_limit:
            self.walk_position_x = float(right_limit)
            self.walk_direction = -1

        self.move(round(self.walk_position_x), self.y())

    def stop_walk(self):
        self.walk_timer.stop()

        self.current_state = "idle"
        self.idle_index = 0
        self.walk_index = 0

        if self.idle_frames:
            self.pet_label.setPixmap(self.idle_frames[0])

        self.last_action = "walk"
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

    # ==================================================
    # Sing
    # ==================================================

    def start_sing(self):
        if not self.sing_frames:
            self.schedule_next_action()
            return

        self.current_state = "sing"
        self.sing_index = 0

        self.wait_sing = False
        self.wait_blink = False
        self.wait_walk = False

        # Sing 播放期间停止其他动作
        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()

        self.sing_timer.start(self.sing_interval)

    def play_sing_frame(self):
        if self.current_state != "sing" or not self.sing_frames:
            return

        self.pet_label.setPixmap(
            self.sing_frames[self.sing_index]
        )
        self.sing_index += 1

        # 不限制帧数，读取多少帧就完整播放多少帧
        if self.sing_index >= len(self.sing_frames):
            self.stop_sing()

    def stop_sing(self):
        self.sing_timer.stop()

        self.current_state = "idle"
        self.last_action = "sing"
        self.idle_index = 0
        self.sing_index = 0

        if self.idle_frames:
            self.pet_label.setPixmap(self.idle_frames[0])

        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

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