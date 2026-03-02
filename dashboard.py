import tkinter as tk
from tkinter import ttk
import subprocess
import pandas as pd
import os

# -------- Functions --------

def start_camera():
    status_label.config(text="Camera Running...")
    subprocess.Popen(["python", "app.py"])

def load_attendance():
    if os.path.exists("attendance.csv"):
        df = pd.read_csv("attendance.csv")

        for row in tree.get_children():
            tree.delete(row)

        for _, r in df.iterrows():
            tree.insert("", "end", values=list(r))
    else:
        status_label.config(text="No attendance file found")


# -------- GUI Window --------
root = tk.Tk()
root.title("Face Attendance Dashboard")
root.geometry("700x500")

title = tk.Label(root, text="Face Recognition Attendance",
                 font=("Arial", 18, "bold"))
title.pack(pady=10)

# Buttons
btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

start_btn = tk.Button(btn_frame, text="Start Camera",
                      command=start_camera, width=15)
start_btn.grid(row=0, column=0, padx=10)

load_btn = tk.Button(btn_frame, text="Show Attendance",
                     command=load_attendance, width=15)
load_btn.grid(row=0, column=1, padx=10)

# Table
columns = ("Name", "Time", "Date")
tree = ttk.Treeview(root, columns=columns, show="headings")

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150)

tree.pack(pady=20, fill="both", expand=True)

# Status
status_label = tk.Label(root, text="Ready", fg="green")
status_label.pack(pady=5)

root.mainloop()
