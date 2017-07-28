import tkinter as tk
import tkinter.font as tkFont
import tkinter.ttk as ttk

import random
import numpy as np
import re

class Application(object):
    def __init__(self, master):
        self.master = master
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Tabs for asset list / shopping cart
        self.notebook = ttk.Notebook(self.master)
        self.notebook.grid(row=0, column=0, sticky='nesw')
        self.notebook.rowconfigure(0, weight=1)
        self.notebook.columnconfigure(0, weight=1)

        # Asset list frame
        self.asset_frame = ttk.Frame(self.notebook, name='asset_frame')
        self.asset_frame.grid(row=0, column=0, sticky='nesw')
        self.asset_frame.rowconfigure(1, weight=1)
        self.asset_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.asset_frame, text='Asset List')

def main():
    root = tk.Tk()
    app = Application(root)
    root.title('Inventory Manager')
    root.update()
    root.mainloop()

if __name__ == '__main__':
    main()
