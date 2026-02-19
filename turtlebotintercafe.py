#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class TurtleBotInterfaceNode(Node):
    def __init__(self, ui_update_cb, log_cmd_cb):
        super().__init__('turtle_bot_interface')

        # Posición (publicada por Coppelia como Twist: linear=(x,y,z))
        self.sub_pos = self.create_subscription(
            Twist, '/turtlebot_position', self.cb_position, 10
        )

        # Comandos (teleop -> Coppelia)
        self.sub_cmd = self.create_subscription(
            Twist, '/turtlebot_cmdVel', self.cb_cmdvel, 10
        )

        self.x_data = []
        self.y_data = []

        self.recording = False
        self.ui_update_cb = ui_update_cb
        self.log_cmd_cb = log_cmd_cb

        self.get_logger().info("turtle_bot_interface listo. Suscrito a /turtlebot_position y /turtlebot_cmdVel.")

    def start_recording(self):
        self.x_data.clear()
        self.y_data.clear()
        self.recording = True

    def stop_recording(self):
        self.recording = False

    def cb_position(self, msg: Twist):
        if not self.recording:
            return
        x = float(msg.linear.x)
        y = float(msg.linear.y)
        self.x_data.append(x)
        self.y_data.append(y)
        self.ui_update_cb()

    def cb_cmdvel(self, msg: Twist):
        # Log de acciones del usuario (cmdVel)
        if not self.recording:
            return
        self.log_cmd_cb(float(msg.linear.x), float(msg.angular.z))


class App:
    def __init__(self):
        rclpy.init()

        # UI
        self.root = tk.Tk()
        self.root.title("TurtleBot2 Interface - Trayectoria")

        # --- Pregunta punto 3: ¿guardar recorrido? (desde interfaz) ---
        self.save_actions = messagebox.askyesno(
            "Guardar recorrido",
            "¿Desea guardar el recorrido (secuencia de acciones) en un archivo .txt?"
        )

        self.actions_file_path = None
        self.actions_fp = None
        self.t0 = None

        if self.save_actions:
            # Pedir nombre de archivo desde la interfaz
            name = simpledialog.askstring("Nombre del archivo", "Ingrese el nombre del archivo (sin .txt):")
            if not name:
                # Si cancela, desactivamos guardado para no bloquear
                self.save_actions = False
            else:
                # Elegir directorio destino
                folder = filedialog.askdirectory(title="Seleccione el directorio donde guardar el .txt")
                if not folder:
                    self.save_actions = False
                else:
                    self.actions_file_path = f"{folder}/{name}.txt"

        # Node ROS (pasa callbacks)
        self.node = TurtleBotInterfaceNode(ui_update_cb=self.refresh_plot, log_cmd_cb=self.log_cmd)

        # Layout controles
        top = tk.Frame(self.root)
        top.pack(padx=10, pady=10, fill="x")

        tk.Label(top, text="Nombre de la gráfica:").pack(side="left")
        self.graph_name_var = tk.StringVar(value="trayectoria_turtlebot2")
        tk.Entry(top, textvariable=self.graph_name_var, width=30).pack(side="left", padx=8)

        self.btn_start = tk.Button(top, text="Start", width=10, command=self.on_start)
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop_save = tk.Button(top, text="Stop & Save", width=12, command=self.on_stop_save)
        self.btn_stop_save.pack(side="left", padx=5)

        # Plot
        self.fig = Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Trayectoria (X vs Y)")
        self.ax.set_xlabel("X (m)")
        self.ax.set_ylabel("Y (m)")
        self.ax.grid(True)
        self.line, = self.ax.plot([], [], linewidth=2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(padx=10, pady=10, fill="both", expand=True)

        # ROS spin integrado con Tk
        self.root.after(20, self.ros_spin_once)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def open_actions_file_if_needed(self):
        if not self.save_actions or self.actions_fp is not None:
            return
        # Abrir archivo y escribir encabezado
        self.actions_fp = open(self.actions_file_path, "w", encoding="utf-8")
        self.actions_fp.write("# linear_x, angular_z, t_seconds\n")
        self.actions_fp.flush()
        self.t0 = time.time()

    def log_cmd(self, linear_x: float, angular_z: float):
        if not self.save_actions:
            return
        if self.actions_fp is None:
            # Se abre cuando empieza el recorrido (Start)
            return
        t = time.time() - self.t0
        self.actions_fp.write(f"{linear_x:.6f},{angular_z:.6f},{t:.6f}\n")
        self.actions_fp.flush()

    def close_actions_file(self):
        if self.actions_fp:
            try:
                self.actions_fp.close()
            except Exception:
                pass
        self.actions_fp = None

    def ros_spin_once(self):
        try:
            rclpy.spin_once(self.node, timeout_sec=0.0)
        except Exception:
            pass
        self.root.after(20, self.ros_spin_once)

    def refresh_plot(self):
        x = self.node.x_data
        y = self.node.y_data
        self.line.set_data(x, y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw_idle()

    def on_start(self):
        # Inicia recorrido + abre .txt si aplica
        self.node.start_recording()
        if self.save_actions:
            self.open_actions_file_if_needed()
            if self.actions_fp is None:
                messagebox.showwarning("Aviso", "Se canceló guardado del .txt. Se continuará sin guardar acciones.")
                self.save_actions = False
            else:
                messagebox.showinfo("Guardado activo", f"Se guardará el recorrido en:\n{self.actions_file_path}")

        self.refresh_plot()

    def on_stop_save(self):
        self.node.stop_recording()

        # Cerrar archivo de acciones si estaba activo
        self.close_actions_file()

        if len(self.node.x_data) < 2:
            messagebox.showwarning("Aviso", "No hay suficientes puntos para guardar la trayectoria.")
            return

        default_name = (self.graph_name_var.get().strip() or "trayectoria_turtlebot2") + ".png"
        filepath = filedialog.asksaveasfilename(
            title="Guardar gráfica",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("PNG Image", "*.png"), ("All files", "*.*")]
        )
        if not filepath:
            return

        self.fig.savefig(filepath)
        messagebox.showinfo("Guardado", f"Gráfica guardada en:\n{filepath}")

    def on_close(self):
        try:
            self.node.stop_recording()
            self.close_actions_file()
            self.node.destroy_node()
            rclpy.shutdown()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    App().run()


if __name__ == "__main__":
    main()

