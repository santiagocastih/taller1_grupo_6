#!/usr/bin/env python3
import sys
import termios
import tty
import select

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


HELP = """
Control TurtleBot2 - Teclado
-----------------------------------------
W: Adelante
S: Atrás
A: Girar izquierda
D: Girar derecha
X: Stop
Q: Salir

Nota: Si no se presiona ninguna tecla, el robot se queda quieto.
(Se publica SOLO cuando cambia el comando, para registrar acciones reales.)
"""


def get_key(timeout=0.1):
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        return sys.stdin.read(1)
    return ''


class TurtleBotTeleop(Node):
    def _init_(self, linear_speed, angular_speed):
        super()._init_('turtle_bot_teleop')

        self.publisher = self.create_publisher(Twist, '/turtlebot_cmdVel', 10)

        self.linear_speed = float(linear_speed)
        self.angular_speed = float(angular_speed)

        # Estado actual publicado (para publicar solo si cambia)
        self.current_lin = 0.0
        self.current_ang = 0.0

        self.get_logger().info("Nodo turtle_bot_teleop iniciado")
        self.get_logger().info(
            f"Velocidad lineal: {self.linear_speed} m/s | "
            f"Velocidad angular: {self.angular_speed} rad/s"
        )
        print(HELP)

        self.timer = self.create_timer(0.05, self.control_loop)

    def publish_if_changed(self, lin, ang):
        if lin == self.current_lin and ang == self.current_ang:
            return
        msg = Twist()
        msg.linear.x = lin
        msg.angular.z = ang
        self.publisher.publish(msg)
        self.current_lin = lin
        self.current_ang = ang

    def control_loop(self):
        key = get_key(0.01)

        # Por defecto: quieto si no hay tecla
        lin = 0.0
        ang = 0.0

        if key == 'w':
            lin = self.linear_speed
        elif key == 's':
            lin = -self.linear_speed
        elif key == 'a':
            ang = self.angular_speed
        elif key == 'd':
            ang = -self.angular_speed
        elif key == 'x':
            lin = 0.0
            ang = 0.0
        elif key == 'q':
            # stop y salir
            self.publish_if_changed(0.0, 0.0)
            self.get_logger().info("Saliendo...")
            rclpy.shutdown()
            return

        # Publica solo si el comando cambió (incluye transición a 0,0)
        self.publish_if_changed(lin, ang)


def main(args=None):
    try:
        linear = float(input("Ingrese velocidad lineal (ej: 0.2): ").strip())
        angular = float(input("Ingrese velocidad angular (ej: 0.6): ").strip())
    except ValueError:
        print("Valores inválidos")
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        rclpy.init(args=args)
        node = TurtleBotTeleop(linear, angular)
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        try:
            # STOP por seguridad
            stop = Twist()
            node.publisher.publish(stop)
            node.destroy_node()
        except Exception:
            pass
        rclpy.shutdown()


if _name_ == '_main_':
    main()