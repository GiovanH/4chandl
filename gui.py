import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

import enum


class Result(enum.Enum):
    RUNNING = enum.auto()
    NEXT = enum.auto()
    DONE = enum.auto()
    CANCEL = enum.auto()


class SelectorWindow(tk.Tk):
    def __init__(self, boardname, headers, tablerows, selectionNos, *args, **kwargs):
        super(SelectorWindow, self).__init__(*args, **kwargs)

        self.cancel = False
        self.selections = None
        self.RESULT = Result.RUNNING

        self.protocol("WM_DELETE_WINDOW", self.cmd_cancel)
        self.bind("<Escape>", self.cmd_done)

        self.SelectorFrame = SelectorFrame(
            self, 
            "/{}/ threads".format(boardname), 
            headers, 
            tablerows, 
            selectionNos
        )
        self.SelectorFrame.grid(sticky="nsew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.geometry("600x800")

        self.mainloop()

    def cmd_cancel(self, event=None):
        self.cancel = True
        self.RESULT = Result.CANCEL
        self.destroy()

    def cmd_done(self, event=None):
        self.selections = self.SelectorFrame.getSelections()
        self.RESULT = Result.DONE
        self.destroy()


class SelectorFrame(tk.Frame):

    # Init and window management
    def __init__(self, parent, title, headers, items, selectionNos, *args, **kwargs):

        if "ID" not in headers:
            raise AssertionError("SelectorFrame MUST have data field 'ID'!")

        tk.Frame.__init__(self, parent, *args, **kwargs)

        # Setup GUI parts
        lab_title = lab_title = tk.Label(self, text=title, font=("Helvetica", 24))
        lab_title.grid(row=0, column=0, sticky="we")

        listbox_threads = tkit.MultiColumnListbox(self, headers, items, multiselect=True, hscroll=True)
        listbox_threads.grid(row=1, column=0, sticky="nsew", padx=(4, 18))

        # Buttons, in a frame
        frame_buttons = tk.Frame(self)
        frame_buttons.grid(row=2, column=0, sticky="sew")

        # Space buttons evenly
        frame_buttons.grid_columnconfigure(0, weight=1)
        frame_buttons.grid_columnconfigure(1, weight=1)

        btn_done = ttk.Button(frame_buttons, text="Save and Continue", command=parent.cmd_done)
        btn_done.grid(row=0, column=1, sticky="sew", padx=4, pady=4)

        btn_cancel = ttk.Button(frame_buttons, text="Save and Update", command=parent.cmd_cancel)
        btn_cancel.grid(row=0, column=0, sticky="sew", padx=4, pady=4)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Expose interfaces
        self.listbox_threads = listbox_threads

        # Load data
        listbox_threads.modSelection(selectionNos)

        # for w in [self, lab_title, listbox_threads, frame_buttons, btn_cancel, btn_done]:
        #     print(w, "in", w.master)

    def getSelections(self):
        return self.listbox_threads.getSelections()
