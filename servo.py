#!/usr/bin/env python3
# coding=utf-8

import inkex
from inkex import PathElement, CubicSuperPath
import os
import math

class ServoController(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--servo-up-command", type=str, default="M5")
        pars.add_argument("--servo-down-command", type=str, default="M3")
        pars.add_argument("--fast-speed", type=float, default=1000)
        pars.add_argument("--slow-speed", type=float, default=500)
        pars.add_argument("--speed-threshold", type=float, default=1.0)
        pars.add_argument("--servo-pwm", type=int, default=90)
        pars.add_argument("--delay", type=float, default=0.5)
        pars.add_argument("--segments", type=int, default=10)
        pars.add_argument("--directory", type=str, default="")
        pars.add_argument("--filename", type=str, default="servo.gcode")
        pars.add_argument("--add-numeric-suffix-to-filename", type=inkex.Boolean, default=True)

    def effect(self):
        if not self.svg.selection:
            inkex.errormsg("❗ Нічого не вибрано для експорту!")
            return

        up_cmd = self.options.servo_up_command
        down_cmd = self.options.servo_down_command
        fast_speed = self.options.fast_speed
        slow_speed = self.options.slow_speed
        speed_threshold = self.options.speed_threshold
        pwm = self.options.servo_pwm
        delay = self.options.delay
        segments = self.options.segments
        directory = self.options.directory or os.getcwd()
        filename = self.options.filename
        add_suffix = self.options.add_numeric_suffix_to_filename

        pwm = max(0, min(1000, pwm))

        full_path = os.path.join(directory, filename)
        if add_suffix:
            base, ext = os.path.splitext(full_path)
            counter = 1
            while os.path.exists(full_path):
                full_path = f"{base}_{counter}{ext}"
                counter += 1

        try:
            svg_height = self.svg.unittouu(self.document.getroot().get('height'))
        except Exception as e:
            inkex.errormsg(f"⚠️ Помилка визначення висоти SVG: {str(e)}")
            return

        gcode = []
        gcode.append("; Generated G-code with adaptive speeds")
        gcode.append("G21 ; Set units to millimeters")
        gcode.append("G90 ; Absolute positioning")
        gcode.append("G4 P0.2 ; Pause for initialization")
        gcode.append(f"{up_cmd} ; Перо підняте")

        for elem in self.svg.selection.filter(PathElement).values():
            path = elem.path.transform(elem.composed_transform())
            csp = CubicSuperPath(path)

            for contour in csp:
                if len(contour) < 2:
                    continue

                points = []
                for i in range(1, len(contour)):
                    for j in range(segments + 1):
                        t = j / segments
                        x = ((1 - t) ** 3 * contour[i - 1][1][0] +
                             3 * (1 - t) ** 2 * t * contour[i - 1][2][0] +
                             3 * (1 - t) * t ** 2 * contour[i][0][0] +
                             t ** 3 * contour[i][1][0])
                        y = ((1 - t) ** 3 * contour[i - 1][1][1] +
                             3 * (1 - t) ** 2 * t * contour[i - 1][2][1] +
                             3 * (1 - t) * t ** 2 * contour[i][0][1] +
                             t ** 3 * contour[i][1][1])
                        y_flipped = svg_height - y
                        points.append((x, y_flipped))

                if not points:
                    continue

                gcode.append(f"G0 X{points[0][0]:.3f} Y{points[0][1]:.3f} F{fast_speed}")
                gcode.append(f"G4 P{delay}")
                gcode.append(f"{down_cmd} S{pwm} ; Перо опущено")
                gcode.append(f"G4 P{delay}")

                for idx in range(1, len(points)):
                    x1, y1 = points[idx - 1]
                    x2, y2 = points[idx]
                    distance = math.hypot(x2 - x1, y2 - y1)

                    speed = slow_speed if distance < speed_threshold else fast_speed
                    gcode.append(f"G1 X{x2:.3f} Y{y2:.3f} F{speed}")

                gcode.append(f"{up_cmd} ; Перо підняте")
                gcode.append(f"G4 P{delay}")

        gcode.append("G0 X0 Y0 ; Повернення в нульові координати")
        gcode.append("M2 ; End of program")

        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write("\n".join(gcode))
            inkex.utils.debug(f"✅ G-code файл успішно створено: {full_path}")
        except Exception as e:
            inkex.errormsg(f"❌ Помилка запису файлу: {str(e)}")

if __name__ == '__main__':
    ServoController().run()
