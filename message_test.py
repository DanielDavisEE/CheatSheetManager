import tkinter as tk
from tkinter import messagebox

options = {}
messagebox.showinfo(title="showinfo", message="message", **options)


messagebox.showwarning(title="showwarning", message="message", **options)
messagebox.showerror(title="showerror", message="message", **options)


messagebox.askquestion(title="askquestion", message="message", **options)
messagebox.askokcancel(title="askokcancel", message="message", **options)
messagebox.askretrycancel(title="askretrycancel", message="message", **options)
messagebox.askyesno(title="askyesno", message="message", **options)
messagebox.askyesnocancel(title="askyesnocancel", message="message", **options)