import random
import re
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QCursor,
    QGuiApplication,
    QPainter,
    QPixmap,
    QTransform,
)


class AnimationManager:
    def __init__(self, pet, base_path: Path, pet_size: int):
        self.pet = pet
        self.base_path = base_path
        self.pet_size = pet_size
        self.current_state = "idle"
        self.last_action = "idle"

        self.idle_frames = self.load_animation_frames(
            self.base_path / "assets" / "idle", "idle_*.png"
        )
        self.idle_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.idle_frames
        ]
        eye_tracking_path = self.base_path / "assets" / "idle_pupils"
        self.idle_base = self.load_image(
            eye_tracking_path / "idle_base.png"
        )
        self.idle_pupils = self.load_image(
            eye_tracking_path / "idle_pupils.png"
        )
        self.idle_eye_mask = self.load_image(
            eye_tracking_path / "idle_eye_mask.png"
        )
        self.eye_tracking_enabled = all(
            frame is not None
            for frame in (
                self.idle_base,
                self.idle_pupils,
                self.idle_eye_mask,
            )
        )
        if self.eye_tracking_enabled:
            mirror_transform = QTransform().scale(-1, 1)
            self.idle_base_right = self.idle_base.transformed(
                mirror_transform,
                Qt.SmoothTransformation,
            )
            self.idle_pupils_right = self.idle_pupils.transformed(
                mirror_transform,
                Qt.SmoothTransformation,
            )
            self.idle_eye_mask_right = self.idle_eye_mask.transformed(
                mirror_transform,
                Qt.SmoothTransformation,
            )
        else:
            self.idle_base_right = None
            self.idle_pupils_right = None
            self.idle_eye_mask_right = None
        self.eye_tracking_radius = 450.0
        self.eye_max_offset = 5.0
        self.eye_max_up_offset = 3.0
        self.blink_frames = self.load_animation_frames(
            self.base_path / "assets" / "blink", "blink_*.png"
        )
        self.sing_frames = self.load_animation_frames(
            self.base_path / "assets" / "sing", "sing_*.png"
        )
        self.walk_frames_left = self.load_animation_frames(
            self.base_path / "assets" / "walk", "walk_*.png"
        )
        self.walk_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.walk_frames_left
        ]
        self.walk_frames = self.walk_frames_left

        self.idle_index = 0
        self.blink_index = 0
        self.walk_index = 0
        self.sing_index = 0

        print(f"Idle 帧数：{len(self.idle_frames)}")
        print(f"Blink 帧数：{len(self.blink_frames)}")
        print(f"Walk 帧数：{len(self.walk_frames)}")
        print(f"Sing 帧数：{len(self.sing_frames)}")

        self.idle_interval = 70
        self.blink_interval = 80
        self.walk_interval = 33
        self.sing_interval = 50

        self.idle_timer = QTimer(self.pet)
        self.idle_timer.timeout.connect(self.play_idle_frame)

        self.blink_timer = QTimer(self.pet)
        self.blink_timer.timeout.connect(self.play_blink_frame)

        self.walk_timer = QTimer(self.pet)
        self.walk_timer.setTimerType(Qt.PreciseTimer)
        self.walk_timer.timeout.connect(self.play_walk_frame)

        self.sing_timer = QTimer(self.pet)
        self.sing_timer.setTimerType(Qt.PreciseTimer)
        self.sing_timer.timeout.connect(self.play_sing_frame)

        self.action_timer = QTimer(self.pet)
        self.action_timer.setSingleShot(True)
        self.action_timer.timeout.connect(self.choose_next_action)

        self.saved_state = None

        self.walk_distance_per_cycle = 95.0
        self.walk_move_per_frame = (
            self.walk_distance_per_cycle / max(1, len(self.walk_frames))
        )
        self.walk_position_x = float(self.pet.x())
        self.walk_direction = 1
        # 原始素材朝左；记录最后实际显示的方向供 idle 使用。
        self.facing_direction = -1
        self.walk_loops_remaining = 0

    def start(self):
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

    @staticmethod
    def get_frame_number(image_path: Path) -> int:
        numbers = re.findall(r"\d+", image_path.stem)
        return int(numbers[-1]) if numbers else 0

    def load_image(self, image_path: Path):
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return None
        return pixmap.scaled(
            self.pet_size,
            self.pet_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def load_animation_frames(self, folder: Path, filename_pattern: str):
        frames = []
        if not folder.exists():
            print(f"文件夹不存在：{folder}")
            return frames

        files = sorted(
            folder.glob(filename_pattern),
            key=self.get_frame_number,
        )
        for image_path in files:
            frame = self.load_image(image_path)
            if frame is None:
                print(f"无法读取图片：{image_path}")
            else:
                frames.append(frame)
        return frames

    def schedule_next_action(self):
        if self.current_state == "idle":
            self.action_timer.start(random.randint(2000, 5000))

    def choose_next_action(self):
        if self.current_state != "idle":
            return

        roll = random.randint(1, 100)
        print(f"随机动作点数：{roll}")

        if roll <= 30:
            print("本次动作：Idle")
            self.last_action = "idle"
            self.schedule_next_action()
        elif roll <= 40:
            print("本次动作：Blink")
            self.start_blink()
        elif roll <= 90:
            print("本次动作：Walk")
            self.start_walk()
        else:
            if self.last_action == "sing":
                print("Sing 被跳过：上一个动作也是 Sing")
                self.schedule_next_action()
            else:
                print("本次动作：Sing")
                self.start_sing()

    def play_idle_frame(self):
        if self.current_state != "idle" or not self.idle_frames:
            return
        self.pet.pet_label.setPixmap(
            self.get_idle_frame(self.idle_index)
        )
        self.idle_index = (self.idle_index + 1) % len(self.idle_frames)

    def get_idle_frame(self, frame_index):
        if self.eye_tracking_enabled:
            return self.render_eye_tracking_idle()
        if self.facing_direction == 1:
            return self.idle_frames_right[frame_index]
        return self.idle_frames[frame_index]

    def render_eye_tracking_idle(self):
        """按底图、眼球、眼眶遮罩的顺序绘制普通待机状态。"""
        canvas = QPixmap(self.pet_size, self.pet_size)
        canvas.fill(Qt.transparent)

        base = self.idle_base
        pupils = self.idle_pupils
        eye_mask = self.idle_eye_mask

        if self.facing_direction == 1:
            base = self.idle_base_right
            pupils = self.idle_pupils_right
            eye_mask = self.idle_eye_mask_right

        layer_x = (self.pet_size - base.width()) // 2
        layer_y = (self.pet_size - base.height()) // 2
        pupil_offset_x, pupil_offset_y = self.get_pupil_offset()

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 最下层：人物底图和眼白。
        painter.drawPixmap(layer_x, layer_y, base)
        # 中间层：仅眼球层随鼠标小幅移动。
        painter.drawPixmap(
            layer_x + pupil_offset_x,
            layer_y + pupil_offset_y,
            pupils,
        )
        # 最上层：人物前景和眼眶遮罩，挡住越出眼眶的部分。
        painter.drawPixmap(layer_x, layer_y, eye_mask)
        painter.end()

        return canvas

    def get_pupil_offset(self):
        """计算受距离和最大幅度限制的眼球位移。"""
        label_center_global = self.pet.pet_label.mapToGlobal(
            self.pet.pet_label.rect().center()
        )
        cursor_position = QCursor.pos()
        delta_x = cursor_position.x() - label_center_global.x()
        delta_y = cursor_position.y() - label_center_global.y()
        distance = (delta_x ** 2 + delta_y ** 2) ** 0.5

        if distance == 0 or distance > self.eye_tracking_radius:
            return 0, 0

        offset_length = min(
            self.eye_max_offset,
            distance * 0.04,
        )
        offset_x = round(delta_x / distance * offset_length)
        offset_y = round(delta_y / distance * offset_length)

        # 上眼眶空间较窄，只缩小向上的范围；其余方向保持不变。
        if offset_y < 0:
            offset_y = max(
                offset_y,
                -round(self.eye_max_up_offset),
            )

        return offset_x, offset_y

    def start_blink(self):
        if not self.blink_frames:
            self.schedule_next_action()
            return
        self.current_state = "blink"
        self.blink_index = 0
        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.start(self.blink_interval)

    def play_blink_frame(self):
        if self.current_state != "blink":
            return
        if self.blink_index < len(self.blink_frames):
            self.pet.pet_label.setPixmap(self.blink_frames[self.blink_index])
            self.blink_index += 1
            return

        self.blink_timer.stop()
        self.current_state = "idle"
        self.last_action = "blink"
        self.idle_index = 0
        self.blink_index = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

    def start_walk(self):
        if not self.walk_frames:
            self.schedule_next_action()
            return
        self.current_state = "walk"
        self.walk_index = 0
        self.action_timer.stop()
        self.idle_timer.stop()
        self.walk_direction = random.choice([-1, 1])
        self.walk_loops_remaining = random.randint(1, 2)
        self.walk_position_x = float(self.pet.x())
        self.walk_timer.start(self.walk_interval)

    def get_walk_frame(self):
        if self.walk_direction == 1:
            return self.walk_frames_right[self.walk_index]
        return self.walk_frames_left[self.walk_index]

    def play_walk_frame(self):
        if self.current_state != "walk" or not self.walk_frames:
            return
        self.facing_direction = self.walk_direction
        self.pet.pet_label.setPixmap(self.get_walk_frame())
        self.move_pet_one_frame()
        self.walk_index += 1
        if self.walk_index >= len(self.walk_frames):
            self.walk_index = 0
            self.walk_loops_remaining -= 1
            if self.walk_loops_remaining <= 0:
                self.stop_walk()

    def move_pet_one_frame(self):
        if self.current_state != "walk" or self.pet.is_dragging:
            return

        screen = QGuiApplication.screenAt(
            self.pet.frameGeometry().center()
        )
        if screen is None:
            screen = QGuiApplication.primaryScreen()

        available = screen.availableGeometry()
        left_limit = available.left()
        right_limit = available.right() - self.pet.width() + 1

        self.walk_position_x += (
            self.walk_move_per_frame * self.walk_direction
        )

        if self.walk_position_x <= left_limit:
            self.walk_position_x = float(left_limit)
            self.walk_direction = 1
        elif self.walk_position_x >= right_limit:
            self.walk_position_x = float(right_limit)
            self.walk_direction = -1

        self.pet.move(round(self.walk_position_x), self.pet.y())

    def stop_walk(self):
        self.walk_timer.stop()
        self.current_state = "idle"
        self.last_action = "walk"
        self.idle_index = 0
        self.walk_index = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

    def start_sing(self):
        if not self.sing_frames:
            self.schedule_next_action()
            return
        self.current_state = "sing"
        self.sing_index = 0
        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.start(self.sing_interval)

    def play_sing_frame(self):
        if self.current_state != "sing" or not self.sing_frames:
            return
        self.pet.pet_label.setPixmap(self.sing_frames[self.sing_index])
        self.sing_index += 1
        if self.sing_index >= len(self.sing_frames):
            self.stop_sing()

    def stop_sing(self):
        self.sing_timer.stop()
        self.current_state = "idle"
        self.last_action = "sing"
        self.idle_index = 0
        self.sing_index = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()

    def pause_for_drag(self):
        self.saved_state = self.current_state
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.stop()
        self.action_timer.stop()

    def resume_idle(self):
        self.current_state = "idle"
        self.last_action = "idle"
        self.idle_index = 0
        self.blink_index = 0
        self.walk_index = 0
        self.sing_index = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()
