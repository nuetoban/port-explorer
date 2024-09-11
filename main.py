import pprint
import threading
import time
import tkinter as tk
from typing import Optional
import psutil
import ctypes as ct


active_port_colors = {
    0: "#00FF00",
    1: "#008800",
    2: "#004400",
    3: "#002200",
}
inactive_port_color = "#222222"
window_bg_color = "black"
text_color = active_port_colors[0]

conn_info = {}


def dark_title_bar(window):
    """
    MORE INFO:
    https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
    """
    window.update()
    set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
    get_parent = ct.windll.user32.GetParent
    hwnd = get_parent(window.winfo_id())
    value = 2
    value = ct.c_int(value)
    set_window_attribute(hwnd, 20, ct.byref(value), 4)


def get_used_ports():
    """Returns a list of all used ports on the system."""

    used_ports_l = []
    used_ports_r = []
    for connection in psutil.net_connections():
        # print(connection)
        try:
            lport = connection.laddr.port  # type: ignore
            rport = connection.raddr.port  # type: ignore

            if connection.status == "ESTABLISHED":
                if connection.laddr.ip == connection.raddr.ip:  # type: ignore
                    continue
                used_ports_l.append(lport)
                used_ports_r.append(rport)

            conn_info[lport] = connection
            conn_info[rport] = connection
        except AttributeError:
            pass

    return used_ports_l + used_ports_r


# Create the main window
root = tk.Tk()
dark_title_bar(root)
root.title("Port Heatmap")  # Set window title
root.configure(background=window_bg_color)
root.state("zoomed")


def close():
    # portinfo.destroy()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", close)
# portinfo.protocol("WM_DELETE_WINDOW", close)


# Get screen dimensions
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Set window dimensions to 80% of screen size
width = int(screen_width)
height = int(screen_height)
canvas_height = height - 200

# root.geometry(
#     f"{width}x{height}+{int((screen_width - width)/2)}+{int((screen_height - height)/2)}"
# )


def get_process_by_pid(pid):
    """Returns the process object corresponding to the given PID.

    Args:
        pid: The process ID (PID) to search for.

    Returns:
        The process object if found, otherwise None.
    """
    try:
        process = psutil.Process(pid)
        return process
    except psutil.NoSuchProcess:
        return None


canvas = tk.Canvas(
    root,
    width=width,
    height=canvas_height,
    bg=window_bg_color,
    highlightthickness=0,
)
root.update()

for c in range(3):
    root.columnconfigure(index=c, weight=1)

for r in range(2):
    root.rowconfigure(index=r, weight=1)

canvas.grid(row=0, column=0, columnspan=3, sticky="nw")
port_label = tk.Label(
    root,
    text="",
    font=("Arial", 10),
    fg=text_color,
    bg=window_bg_color,
    justify="left",
    height=9,
    width=5,
)
# port_label.pack(pady=10, padx=10, anchor="nw")  # Add some padding around the label
port_label.grid(row=1, column=0, sticky="nsew")

conn_label = tk.Label(
    root,
    text="",
    font=("Arial", 10),
    fg=text_color,
    bg=window_bg_color,
    justify="left",
    height=9,
    width=5,
)
# conn_label.pack(pady=10, padx=10)  # Add some padding around the label
conn_label.grid(row=1, column=1, sticky="nsew")

process_label = tk.Label(
    root,
    text="",
    font=("Arial", 10),
    fg=text_color,
    bg=window_bg_color,
    # bg="white",
    justify="left",
    height=9,
    width=5,
)
# process_label.pack(pady=10, padx=10)  # Add some padding around the label
process_label.grid(row=1, column=2, sticky="nsew")
# canvas.pack()


rect_size = 4
padding = 5
x_extra = 0
y_extra = 0

port_rects = {}


def addr_to_string(addr):
    return f"{addr.ip}:{addr.port}"


def conn_to_string(conn) -> str:
    if conn is None:
        return ""

    return f"""
+ fd: {conn.fd}
+ family: {conn.family.__repr__()}
+ type: {conn.type.__repr__()}
+ laddr: {addr_to_string(conn.laddr)}
+ raddr: {addr_to_string(conn.raddr)}
+ status: {conn.status}
+ pid: {conn.pid}
      """.strip()


def process_to_string(process: Optional[psutil.Process]) -> str:
    if process is None:
        return ""
    return f"""
+ pid: {process.pid}
+ name: {process.name()}
+ status: {process.status()}
      """.strip()


def make_show_port_info(port):
    def show(*args):
        info = conn_info.get(port)
        process = None
        if info is not None:
            process = get_process_by_pid(info.pid)

        text = f"""
Port: {port}

Conn
{conn_to_string(info)}

Process
{process_to_string(process)}
""".strip()
        port_label.config(text=str(port))
        conn_label.config(text=conn_to_string(info))
        process_label.config(text=process_to_string(process))
        # portinfo.update()

    return show


for i in range(1, 2**16):
    x1, y1 = 10 + x_extra, 10 + y_extra
    x2, y2 = 10 + rect_size + x_extra, 10 + y_extra + rect_size

    rectangle = canvas.create_rectangle(
        x1,
        y1,
        x2,
        y2,
        fill=inactive_port_color,
        width=0,
    )
    # rectangle.bind('<Enter>')
    canvas.tag_bind(rectangle, "<Enter>", make_show_port_info(i))
    port_rects[i] = rectangle
    y_extra += padding

    # if i % (int(height / padding) - padding * 30) == 0:
    #     x_extra += padding
    #     y_extra = 0

    if y2 + padding * 2 > canvas_height:
        x_extra += padding
        y_extra = 0


active_ports = {}


def refresh_ports():
    global port_rects
    global active_ports

    while True:
        time.sleep(0.3)

        # Update ports colors
        for port, color in active_ports.items():
            if color is None:
                continue

            if color >= 3:
                active_ports[port] = None
            else:
                active_ports[port] = color + 1

        # Update active ports
        for port in get_used_ports():
            active_ports[port] = 0

        # Update colors
        for port, color in active_ports.items():
            if color is not None:
                canvas.itemconfig(port_rects[port], fill=active_port_colors[color])
            else:
                canvas.itemconfig(port_rects[port], fill=inactive_port_color)

        root.update()
        # portinfo.update()


background_thread = threading.Thread(target=refresh_ports)
background_thread.daemon = True
background_thread.start()

# Start the event loop
root.mainloop()
