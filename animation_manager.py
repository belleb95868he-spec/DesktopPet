import random
import re
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QCursor,
    QGuiApplication,
    QPainter,
    QPixmap,
    QTransform,
)

WORK_ENTER_PROBABILITY = 0.10
WORK_DURATION_MS = 2 * 60 * 1000
WORK_COOLDOWN_MS = 10 * 60 * 1000
WORK_BLINK_INTERVAL_MS = 3000
WORK_BLINK_FRAME_INTERVAL_MS = 100
WORK_REWARD_INTERVAL_MS = 10 * 1000
WORK_REWARD_PER_INTERVAL = 10
IDLE_ENTER_PROBABILITY = 0.20
BLINK_ENTER_PROBABILITY = 0.40
WALK_ENTER_PROBABILITY = 0.20
SING_ENTER_PROBABILITY = 0.10
HUNGRY_ENTER_PROBABILITY = 0.40
LOW_HUNGER_IDLE_PROBABILITY = 0.30
LOW_HUNGER_BLINK_PROBABILITY = 0.30
HUNGRY_THRESHOLD = 30
HUNGRY_FRAME_INTERVAL_MS = 47
HUNGRY_COOLDOWN_MS = 30 * 1000
PETTING_FRAME_INTERVAL_MS = 47
EAT_FRAME_INTERVAL_MS = 33


class AnimationManager:
    def __init__(self, pet, base_path: Path, pet_size: int):
        self.pet = pet
        self.base_path = base_path
        self.pet_size = pet_size
        screen = QGuiApplication.primaryScreen()
        self.device_pixel_ratio = (
            max(1.0, screen.devicePixelRatio())
            if screen is not None
            else 1.0
        )
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
        self.eye_tracking_radius = 200.0
        self.eye_max_offset = 5.0
        self.eye_max_up_offset = 3.0
        self.eye_smoothing_factor = 0.6
        self.eye_current_offset_x = 0.0
        self.eye_current_offset_y = 0.0
        self.blink_frames = self.load_animation_frames(
            self.base_path / "assets" / "blink", "blink_*.png"
        )
        self.blink_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.blink_frames
        ]
        self.sing_frames = self.load_animation_frames(
            self.base_path / "assets" / "sing", "sing_*.png"
        )
        self.sing_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.sing_frames
        ]
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
        self.work_frame = self.load_image(
            self.base_path / "assets" / "work" / "work.png"
        )
        self.work_blink_frames = self.load_animation_frames(
            self.base_path / "assets" / "work_blink",
            "work_blink*.png",
        )
        if len(self.work_blink_frames) == 3:
            self.work_blink_sequence = [
                self.work_blink_frames[0],
                self.work_blink_frames[1],
                self.work_blink_frames[2],
            ]
        else:
            self.work_blink_sequence = []
        self.hungry_frames_left = self.load_animation_frames(
            self.base_path / "assets" / "hungry",
            "hungry_*.png",
        )
        self.hungry_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.hungry_frames_left
        ]
        self.petting_frames_left = self.load_animation_frames(
            self.base_path / "assets" / "petting",
            "petting_*.png",
        )
        self.petting_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.petting_frames_left
        ]
        self.eat_frames_left = self.load_animation_frames(
            self.base_path / "assets" / "eat",
            "eat_*.png",
        )
        self.eat_frames_right = [
            frame.transformed(
                QTransform().scale(-1, 1),
                Qt.SmoothTransformation,
            )
            for frame in self.eat_frames_left
        ]

        self.idle_index = 0
        self.blink_index = 0
        self.walk_index = 0
        self.sing_index = 0

        print(f"Idle 帧数：{len(self.idle_frames)}")
        print(f"Blink 帧数：{len(self.blink_frames)}")
        print(f"Walk 帧数：{len(self.walk_frames)}")
        print(f"Sing 帧数：{len(self.sing_frames)}")
        print(f"Hungry 帧数：{len(self.hungry_frames_left)}")
        print(f"Petting 帧数：{len(self.petting_frames_left)}")
        print(f"Eat 帧数：{len(self.eat_frames_left)}")

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

        self.hungry_timer = QTimer(self.pet)
        self.hungry_timer.setInterval(HUNGRY_FRAME_INTERVAL_MS)
        self.hungry_timer.setTimerType(Qt.PreciseTimer)
        self.hungry_timer.timeout.connect(self.play_hungry_frame)

        self.petting_timer = QTimer(self.pet)
        self.petting_timer.setInterval(PETTING_FRAME_INTERVAL_MS)
        self.petting_timer.setTimerType(Qt.PreciseTimer)
        self.petting_timer.timeout.connect(self.play_petting_frame)

        self.eat_timer = QTimer(self.pet)
        self.eat_timer.setInterval(EAT_FRAME_INTERVAL_MS)
        self.eat_timer.setTimerType(Qt.PreciseTimer)
        self.eat_timer.timeout.connect(self.play_eat_frame)

        self.action_timer = QTimer(self.pet)
        self.action_timer.setSingleShot(True)
        self.action_timer.timeout.connect(self.choose_next_action)

        self.work_end_timer = QTimer(self.pet)
        self.work_end_timer.setSingleShot(True)
        self.work_end_timer.setTimerType(Qt.PreciseTimer)
        self.work_end_timer.timeout.connect(self.finish_work)

        self.work_reward_timer = QTimer(self.pet)
        self.work_reward_timer.setInterval(WORK_REWARD_INTERVAL_MS)
        self.work_reward_timer.setTimerType(Qt.PreciseTimer)
        self.work_reward_timer.timeout.connect(
            self.claim_work_interval_rewards
        )

        self.work_blink_interval_timer = QTimer(self.pet)
        self.work_blink_interval_timer.setInterval(
            WORK_BLINK_INTERVAL_MS
        )
        self.work_blink_interval_timer.timeout.connect(
            self.start_work_blink
        )

        self.work_blink_frame_timer = QTimer(self.pet)
        self.work_blink_frame_timer.setInterval(
            WORK_BLINK_FRAME_INTERVAL_MS
        )
        self.work_blink_frame_timer.timeout.connect(
            self.play_work_blink_frame
        )

        self.work_blink_frame_index = 0
        self.work_blink_playing = False
        self.work_entry_available = True
        self.idle_cycles_before_actions = 0
        self.work_started_at = None
        self.work_reward_intervals_claimed = 0
        self.work_cooldown_until = 0.0
        self.hungry_index = 0
        self.hungry_loops_remaining = 0
        self.hungry_cooldown_until = 0.0
        self.petting_index = 0
        self.eat_index = 0

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
        target_size = round(self.pet_size * self.device_pixel_ratio)
        scaled = pixmap.scaled(
            target_size,
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(self.device_pixel_ratio)
        return scaled

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
        if (
            self.current_state == "idle"
            and self.idle_cycles_before_actions == 0
        ):
            self.action_timer.start(random.randint(2000, 5000))

    def choose_next_action(self):
        if self.current_state != "idle":
            return

        roll = random.randint(1, 100)
        print(f"随机动作点数：{roll}")

        if self.pet.status_manager.hunger < HUNGRY_THRESHOLD:
            hungry_available = (
                bool(self.hungry_frames_left)
                and time.monotonic() >= self.hungry_cooldown_until
            )

            if hungry_available:
                hungry_limit = round(
                    HUNGRY_ENTER_PROBABILITY * 100
                )
                low_hunger_idle_limit = hungry_limit + round(
                    LOW_HUNGER_IDLE_PROBABILITY * 100
                )
                low_hunger_blink_limit = (
                    low_hunger_idle_limit
                    + round(LOW_HUNGER_BLINK_PROBABILITY * 100)
                )
                if roll <= hungry_limit:
                    print("本次动作：Hungry")
                    self.start_hungry()
                elif roll <= low_hunger_idle_limit:
                    self.choose_idle_action()
                elif roll <= low_hunger_blink_limit:
                    print("本次动作：Blink")
                    self.start_blink()
                else:
                    self.choose_idle_action()
            elif roll <= 50:
                self.choose_idle_action()
            else:
                print("本次动作：Blink")
                self.start_blink()
            return

        idle_limit = round(IDLE_ENTER_PROBABILITY * 100)
        blink_limit = idle_limit + round(
            BLINK_ENTER_PROBABILITY * 100
        )
        walk_limit = blink_limit + round(
            WALK_ENTER_PROBABILITY * 100
        )
        sing_limit = walk_limit + round(
            SING_ENTER_PROBABILITY * 100
        )
        work_limit = sing_limit + round(
            WORK_ENTER_PROBABILITY * 100
        )

        if roll <= idle_limit:
            self.choose_idle_action()
        elif roll <= blink_limit:
            print("本次动作：Blink")
            self.start_blink()
        elif roll <= walk_limit:
            print("本次动作：Walk")
            self.start_walk()
        elif roll <= sing_limit:
            if self.last_action == "sing":
                print("Sing 被跳过：上一个动作也是 Sing")
                self.schedule_next_action()
            else:
                print("本次动作：Sing")
                self.start_sing()
        elif (
            self.work_entry_available
            and self.work_frame is not None
            and self.work_blink_sequence
            and time.monotonic() >= self.work_cooldown_until
        ):
            print("本次动作：Work")
            self.start_work()
        elif roll <= work_limit:
            if time.monotonic() < self.work_cooldown_until:
                print("本次动作：Blink（Work 冷却）")
                self.start_blink()
            else:
                self.choose_idle_action()

    def choose_idle_action(self):
        print("本次动作：Idle")
        self.last_action = "idle"
        self.schedule_next_action()

    def play_idle_frame(self):
        if self.current_state != "idle" or not self.idle_frames:
            return
        self.pet.pet_label.setPixmap(
            self.get_idle_frame(self.idle_index)
        )
        self.idle_index = (self.idle_index + 1) % len(self.idle_frames)
        if (
            self.idle_index == 0
            and self.idle_cycles_before_actions > 0
        ):
            self.idle_cycles_before_actions -= 1
            if self.idle_cycles_before_actions == 0:
                self.work_entry_available = True
                self.schedule_next_action()

    def get_idle_frame(self, frame_index):
        if self.eye_tracking_enabled:
            return self.render_eye_tracking_idle()
        if self.facing_direction == 1:
            return self.idle_frames_right[frame_index]
        return self.idle_frames[frame_index]

    def render_eye_tracking_idle(self):
        """按底图、眼球、眼眶遮罩的顺序绘制普通待机状态。"""
        physical_size = round(
            self.pet_size * self.device_pixel_ratio
        )
        canvas = QPixmap(physical_size, physical_size)
        canvas.fill(Qt.transparent)
        canvas.setDevicePixelRatio(self.device_pixel_ratio)

        base = self.idle_base
        pupils = self.idle_pupils
        eye_mask = self.idle_eye_mask

        if self.facing_direction == 1:
            base = self.idle_base_right
            pupils = self.idle_pupils_right
            eye_mask = self.idle_eye_mask_right

        base_width = base.width() / base.devicePixelRatio()
        base_height = base.height() / base.devicePixelRatio()
        layer_x = round((self.pet_size - base_width) / 2)
        layer_y = round((self.pet_size - base_height) / 2)
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

        target_x = 0.0
        target_y = 0.0
        if 0 < distance <= self.eye_tracking_radius:
            offset_length = min(
                self.eye_max_offset,
                distance * 0.04,
            )
            target_x = delta_x / distance * offset_length
            target_y = delta_y / distance * offset_length

            # 上眼眶空间较窄，只缩小向上的范围。
            if target_y < 0:
                target_y = max(
                    target_y,
                    -self.eye_max_up_offset,
                )

        return self.smooth_pupil_offset(target_x, target_y)

    def smooth_pupil_offset(self, target_x, target_y):
        """平滑跟随目标位置，并在鼠标离开范围后逐渐回正。"""
        factor = self.eye_smoothing_factor
        self.eye_current_offset_x += (
            target_x - self.eye_current_offset_x
        ) * factor
        self.eye_current_offset_y += (
            target_y - self.eye_current_offset_y
        ) * factor

        if abs(self.eye_current_offset_x) < 0.05:
            self.eye_current_offset_x = 0.0
        if abs(self.eye_current_offset_y) < 0.05:
            self.eye_current_offset_y = 0.0

        return (
            round(self.eye_current_offset_x),
            round(self.eye_current_offset_y),
        )

    def start_blink(self):
        if self.is_interaction_locked():
            return
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
            self.pet.pet_label.setPixmap(
                self.get_blink_frame(self.blink_index)
            )
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

    def get_blink_frame(self, frame_index):
        if self.facing_direction == 1:
            return self.blink_frames_right[frame_index]
        return self.blink_frames[frame_index]

    def start_walk(self):
        if self.is_interaction_locked():
            return
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
        if self.is_interaction_locked():
            return
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
        self.pet.pet_label.setPixmap(
            self.get_sing_frame(self.sing_index)
        )
        self.sing_index += 1
        if self.sing_index >= len(self.sing_frames):
            self.stop_sing()

    def get_sing_frame(self, frame_index):
        if self.facing_direction == 1:
            return self.sing_frames_right[frame_index]
        return self.sing_frames[frame_index]

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
        if self.is_interaction_locked():
            return
        self.saved_state = self.current_state
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.stop()
        self.action_timer.stop()
        if self.current_state == "hungry":
            self.hungry_timer.stop()
            self.start_hungry_cooldown()

    def resume_idle(self):
        if self.is_interaction_locked():
            return
        hungry_was_interrupted = self.saved_state == "hungry"
        self.current_state = "idle"
        self.last_action = "idle"
        self.idle_index = 0
        self.blink_index = 0
        self.walk_index = 0
        self.sing_index = 0
        self.hungry_index = 0
        self.hungry_loops_remaining = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.saved_state = None
        if hungry_was_interrupted:
            self.idle_cycles_before_actions = 1
        else:
            self.schedule_next_action()

    def is_interaction_locked(self):
        return self.current_state in {"work", "petting", "eat"}

    def is_petting(self):
        return self.current_state == "petting"

    def start_petting(self):
        """立即切换到摸头动画；播放期间不会重复启动或排队。"""
        if self.current_state in {"work", "petting", "eat"}:
            return False
        if not self.petting_frames_left:
            return False

        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.stop()
        self.hungry_timer.stop()

        self.current_state = "petting"
        self.last_action = "petting"
        self.petting_index = 0
        self.pet.pet_label.setPixmap(self.get_petting_frame(0))
        self.petting_index = 1
        self.petting_timer.start()
        return True

    def get_petting_frame(self, frame_index):
        if self.facing_direction == 1:
            return self.petting_frames_right[frame_index]
        return self.petting_frames_left[frame_index]

    def play_petting_frame(self):
        if self.current_state != "petting":
            self.petting_timer.stop()
            return

        if self.petting_index < len(self.petting_frames_left):
            self.pet.pet_label.setPixmap(
                self.get_petting_frame(self.petting_index)
            )
            self.petting_index += 1
            return

        self.finish_petting()

    def finish_petting(self):
        """摸头动画完整播放一次后回到 idle。"""
        if self.current_state != "petting":
            return False

        self.petting_timer.stop()
        self.current_state = "idle"
        self.last_action = "petting"
        self.petting_index = 0
        self.idle_index = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        if hasattr(self.pet, "refresh_economy_ui"):
            self.pet.refresh_economy_ui()
        self.schedule_next_action()
        return True

    def start_eating(self):
        """Play one complete eating animation without allowing restarts."""
        if self.current_state in {"work", "petting", "eat"}:
            return False
        if not self.eat_frames_left:
            return False

        was_hungry = self.current_state == "hungry"
        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.stop()
        self.hungry_timer.stop()
        if was_hungry:
            self.start_hungry_cooldown()

        self.current_state = "eat"
        self.last_action = "eat"
        self.eat_index = 0
        self.pet.pet_label.setPixmap(self.get_eat_frame(0))
        self.eat_index = 1
        self.eat_timer.start()
        return True

    def get_eat_frame(self, frame_index):
        if self.facing_direction == 1:
            return self.eat_frames_right[frame_index]
        return self.eat_frames_left[frame_index]

    def play_eat_frame(self):
        if self.current_state != "eat":
            self.eat_timer.stop()
            return
        if self.eat_index < len(self.eat_frames_left):
            self.pet.pet_label.setPixmap(
                self.get_eat_frame(self.eat_index)
            )
            self.eat_index += 1
            return
        self.finish_eating()

    def finish_eating(self):
        if self.current_state != "eat":
            return False
        self.eat_timer.stop()
        self.current_state = "idle"
        self.last_action = "eat"
        self.eat_index = 0
        self.idle_index = 0
        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.schedule_next_action()
        return True

    def start_hungry(self):
        if (
            self.current_state != "idle"
            or not self.hungry_frames_left
            or self.pet.status_manager.hunger >= HUNGRY_THRESHOLD
            or time.monotonic() < self.hungry_cooldown_until
        ):
            return False

        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.stop()

        self.current_state = "hungry"
        self.last_action = "hungry"
        self.hungry_index = 0
        self.hungry_loops_remaining = 1
        self.pet.pet_label.setPixmap(self.get_hungry_frame(0))
        self.hungry_index = 1
        self.hungry_timer.start()
        self.pet.dialogue_manager.show_message(
            "有点饿了……",
            duration=3000,
        )
        return True

    def get_hungry_frame(self, frame_index):
        if self.facing_direction == 1:
            return self.hungry_frames_right[frame_index]
        return self.hungry_frames_left[frame_index]

    def play_hungry_frame(self):
        if self.current_state != "hungry":
            self.hungry_timer.stop()
            return

        if self.hungry_index < len(self.hungry_frames_left):
            self.pet.pet_label.setPixmap(
                self.get_hungry_frame(self.hungry_index)
            )
            self.hungry_index += 1
            return

        self.hungry_loops_remaining -= 1
        if self.hungry_loops_remaining > 0:
            self.hungry_index = 0
            return
        self.finish_hungry()

    def start_hungry_cooldown(self):
        self.hungry_cooldown_until = (
            time.monotonic() + HUNGRY_COOLDOWN_MS / 1000
        )

    def finish_hungry(self):
        """结束 hungry，并完成一轮 idle 后再恢复随机动作。"""
        if self.current_state != "hungry":
            return False

        self.hungry_timer.stop()
        self.start_hungry_cooldown()
        self.current_state = "idle"
        self.last_action = "hungry"
        self.hungry_index = 0
        self.hungry_loops_remaining = 0
        self.idle_index = 0
        self.idle_cycles_before_actions = 1

        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        return True

    def stop_hungry_after_feeding(self):
        if (
            self.current_state == "hungry"
            and self.pet.status_manager.hunger >= HUNGRY_THRESHOLD
        ):
            return self.finish_hungry()
        return False

    def start_work(self):
        """从允许切换的 idle 节点进入固定时长的工作状态。"""
        if (
            self.current_state != "idle"
            or not self.work_entry_available
            or self.work_frame is None
            or not self.work_blink_sequence
            or self.work_end_timer.isActive()
            or time.monotonic() < self.work_cooldown_until
        ):
            return False

        self.action_timer.stop()
        self.idle_timer.stop()
        self.blink_timer.stop()
        self.walk_timer.stop()
        self.sing_timer.stop()

        self.current_state = "work"
        self.last_action = "work"
        self.work_entry_available = False
        self.work_blink_frame_index = 0
        self.work_blink_playing = False
        self.work_started_at = time.monotonic()
        self.work_reward_intervals_claimed = 0
        if hasattr(self.pet, "reset_work_coin_gain_animation"):
            self.pet.reset_work_coin_gain_animation()
        self.pet.pet_label.setPixmap(self.work_frame)
        self.pet.status_manager.update_ui()
        self.pet.collapse_status_panel_for_work()

        if hasattr(self.pet, "dialogue_manager"):
            self.pet.dialogue_manager.hide_message()

        self.work_end_timer.start(WORK_DURATION_MS)
        self.work_reward_timer.start()
        self.work_blink_interval_timer.start()
        return True

    def claim_work_interval_rewards(self):
        """Immediately pay each completed 10-second unit of work."""
        if self.current_state != "work" or self.work_started_at is None:
            return 0
        elapsed_ms = min(
            WORK_DURATION_MS,
            (time.monotonic() - self.work_started_at) * 1000,
        )
        completed_intervals = int(
            elapsed_ms // WORK_REWARD_INTERVAL_MS
        )
        newly_completed = max(
            0,
            completed_intervals - self.work_reward_intervals_claimed,
        )
        for _ in range(newly_completed):
            self.pet.status_manager.add_coins(
                WORK_REWARD_PER_INTERVAL
            )
            if hasattr(self.pet, "show_work_coin_gain"):
                self.pet.show_work_coin_gain(
                    WORK_REWARD_PER_INTERVAL
                )
            self.work_reward_intervals_claimed += 1
        return newly_completed

    def start_work_blink(self):
        if (
            self.current_state != "work"
            or self.work_blink_playing
            or not self.work_blink_sequence
        ):
            return

        self.work_blink_playing = True
        self.work_blink_frame_index = 1
        self.pet.pet_label.setPixmap(self.work_blink_sequence[0])
        self.work_blink_frame_timer.start()

    def play_work_blink_frame(self):
        if self.current_state != "work":
            self.work_blink_frame_timer.stop()
            self.work_blink_playing = False
            self.work_blink_frame_index = 0
            return

        if self.work_blink_frame_index < len(
            self.work_blink_sequence
        ):
            self.pet.pet_label.setPixmap(
                self.work_blink_sequence[
                    self.work_blink_frame_index
                ]
            )
            self.work_blink_frame_index += 1
            return

        self.work_blink_frame_timer.stop()
        self.work_blink_frame_index = 0
        self.work_blink_playing = False
        self.pet.pet_label.setPixmap(self.work_frame)

    def finish_work(self):
        """结束 work，强制完成一轮 idle 后再开放随机动作。"""
        if self.current_state != "work":
            return False

        elapsed_ms = (
            time.monotonic() - self.work_started_at
        ) * 1000
        if elapsed_ms < WORK_DURATION_MS:
            return False

        self.claim_work_interval_rewards()

        self.work_end_timer.stop()
        self.work_reward_timer.stop()
        self.work_blink_interval_timer.stop()
        self.work_blink_frame_timer.stop()
        self.work_blink_frame_index = 0
        self.work_blink_playing = False
        self.work_started_at = None
        self.work_cooldown_until = (
            time.monotonic() + WORK_COOLDOWN_MS / 1000
        )

        self.current_state = "idle"
        self.last_action = "work"
        self.idle_index = 0
        self.idle_cycles_before_actions = 1

        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.pet.status_manager.update_ui()
        return True

    def cancel_work(self):
        """Leave work while retaining rewards from completed 10-second units."""
        if self.current_state != "work":
            return False

        self.work_end_timer.stop()
        self.claim_work_interval_rewards()
        self.work_reward_timer.stop()
        self.work_blink_interval_timer.stop()
        self.work_blink_frame_timer.stop()
        self.work_blink_frame_index = 0
        self.work_blink_playing = False
        self.work_started_at = None
        self.work_reward_intervals_claimed = 0
        self.work_cooldown_until = (
            time.monotonic() + WORK_COOLDOWN_MS / 1000
        )

        self.current_state = "idle"
        self.last_action = "work"
        self.idle_index = 0
        self.idle_cycles_before_actions = 1

        if self.idle_frames:
            self.pet.pet_label.setPixmap(self.get_idle_frame(0))
        self.idle_timer.start(self.idle_interval)
        self.pet.status_manager.update_ui()
        return True
