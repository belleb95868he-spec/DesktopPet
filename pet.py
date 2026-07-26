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
    QVBoxLayout,
    QWidget,
)

from animation_manager import AnimationManager
from dialogue import DialogueManager
from hourly_greetings import HourlyGreetingManager
from petting_manager import PettingManager
from status_manager import StatusManager


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

        # ==================================================
        # 心情
        # ==================================================

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

        # ==================================================
        # 饱腹
        # ==================================================

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

        # ==================================================
        # 按钮
        # ==================================================

        button_layout = QHBoxLayout()

        self.feed_button = QPushButton(
            "🍎 喂食"
        )

        self.touch_button = QPushButton(
            "🤲 摸摸"
        )

        self.feed_button.clicked.connect(
            self.status_manager.feed_pet
        )

        self.touch_button.clicked.connect(
            self.status_manager.touch_pet
        )

        button_layout.addWidget(
            self.feed_button
        )

        button_layout.addWidget(
            self.touch_button
        )

        panel_layout.addLayout(
            mood_layout
        )

        panel_layout.addLayout(
            hunger_layout
        )

        panel_layout.addLayout(
            button_layout
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
                    self.drag_start_global = (
                        event.globalPosition().toPoint()
                    )

                    self.window_start_position = (
                        self.pos()
                    )

                    self.is_dragging = False

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
                            self.start_drag()

                    if self.is_dragging:
                        self.current_drag_global = current_global
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

                    event.accept()

                    return True

        return super().eventFilter(
            watched,
            event,
        )

    def start_drag(self):
        self.animation_manager.pause_for_drag()
        if self.lifted_pixmap is not None:
            rotated = self.render_rotated_lifted_pixmap(0.0)
            self.pet_label.setPixmap(rotated)
            self.pet_label.update()

    def stop_drag(self):
        self.animation_manager.resume_idle()

    def update_drag_swing(self):
        if not self.is_dragging:
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

    def toggle_status_panel(self):
        if self.status_panel.isVisible():
            self.status_panel.hide()
        else:
            self.status_panel.show()

        self.adjustSize()

        self.dialogue_manager.update_position()

        self.keep_inside_screen()

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
