#!/usr/bin/env python3
import os
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import tkinter as tk
from tkinter import filedialog, messagebox


class TurtleBotPlayer(Node):
    """
    Al ejecutar:
      1) abre un diálogo visual para seleccionar un .txt
      2) reproduce inmediatamente el recorrido
      3) publica en /turtlebot_cmdVel
      4) al finalizar envía STOP y termina

    Formato del .txt (por línea):
      linear_x,angular_z,t_seconds
    """

    def __init__(self):
        super().__init__('turtle_bot_player')
        self.pub = self.create_publisher(Twist, '/turtlebot_cmdVel', 10)
        self.get_logger().info("turtle_bot_player iniciado (selección de archivo y reproducción inmediata).")

    def select_txt_file(self) -> str:
        root = tk.Tk()
        root.withdraw()

        path = filedialog.askopenfilename(
            title="Seleccione un archivo de recorrido (.txt)",
            filetypes=[("Text files", "*.txt")]
        )

        root.update()
        root.destroy()

        return path

    def publish_cmd(self, lin: float, ang: float):
        msg = Twist()
        msg.linear.x = float(lin)
        msg.angular.z = float(ang)
        self.pub.publish(msg)

    def read_commands(self, path: str):
        cmds = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) != 3:
                    continue
                lin = float(parts[0])
                ang = float(parts[1])
                t = float(parts[2])
                cmds.append((lin, ang, t))
        return cmds

    def play(self):
        path = self.select_txt_file()

        if not path:
            messagebox.showwarning("Cancelado", "No se seleccionó ningún archivo .txt.")
            self.get_logger().warning("No se seleccionó archivo. Saliendo.")
            return

        if not os.path.exists(path):
            messagebox.showerror("Error", f"El archivo no existe:\n{path}")
            self.get_logger().error(f"Archivo no existe: {path}")
            return

        cmds = self.read_commands(path)
        if not cmds:
            messagebox.showerror("Error", "El archivo no contiene comandos válidos.")
            self.get_logger().error("Archivo sin comandos válidos.")
            return

        self.get_logger().info(f"Reproduciendo: {path}")

        prev_t = None
        for lin, ang, t in cmds:
            if prev_t is not None:
                dt = max(0.0, t - prev_t)
                time.sleep(dt)
            self.publish_cmd(lin, ang)
            prev_t = t

        # STOP al final
        self.publish_cmd(0.0, 0.0)
        time.sleep(0.1)

        messagebox.showinfo("Listo", "Recorrido reproducido exitosamente (STOP enviado).")
        self.get_logger().info("Reproducción finalizada (STOP).")


def main(args=None):
    rclpy.init(args=args)
    node = TurtleBotPlayer()

    try:
        node.play()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.publish_cmd(0.0, 0.0)
        except Exception:
            pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
