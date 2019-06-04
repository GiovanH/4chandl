import tkinter as tk
from tkinter import ttk
from snip import tkit

import enum


class Result(enum.Enum):
    RUNNING = enum.auto()
    NEXT = enum.auto()
    ABORT = enum.auto()
    END = enum.auto()


class SelectorWindow(tk.Tk):
    def __init__(self, title, headers, tablerows, selectionNos, saveCallback, *args, **kwargs):
        super(SelectorWindow, self).__init__(*args, **kwargs)

        self.selections = None
        self.initial_selections = selectionNos
        self.RESULT = Result.RUNNING

        self.saveCallback = saveCallback

        self.protocol("WM_DELETE_WINDOW", self.end(Result.ABORT))
        self.bind("<Escape>", self.end(Result.ABORT))

        self.SelectorFrame = SelectorFrame(
            self, 
            title, 
            headers, 
            tablerows, 
            selectionNos
        )
        self.SelectorFrame.grid(sticky="nsew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.geometry("950x800")

        self.mainloop()

    def end(self, result, save=False):
        def _end(event=None):
            if save:
                self.saveSelections()
            self.RESULT = result
            self.destroy()
        return _end

    def resetSelections(self, event=None):
        self.SelectorFrame.listbox_threads.modSelection(self.initial_selections)

    def saveSelections(self, event=None):
        self.saveCallback(self.SelectorFrame.getSelections())


class SelectorFrame(tk.Frame):

    # Init and window management
    def __init__(self, parent, title, headers, items, selectionNos, *args, **kwargs):

        if "ID" not in headers:
            raise AssertionError("SelectorFrame MUST have data field 'ID'!")

        tk.Frame.__init__(self, parent, *args, **kwargs)

        # Setup GUI parts
        lab_title = lab_title = tk.Label(self, text=title, font=("Helvetica", 24))
        lab_title.grid(row=0, column=0, sticky="we")

        listbox_threads = tkit.MultiColumnListbox(self, headers, items, multiselect=True, hscroll=True, nonestr="")
        listbox_threads.grid(row=1, column=0, sticky="nsew", padx=(4, 18))

        # Buttons, in a frame
        frame_buttons = tk.Frame(self)
        frame_buttons.grid(row=2, column=0, sticky="sew")

        # Space buttons evenly
        frame_buttons.grid_columnconfigure(0, weight=1)
        frame_buttons.grid_columnconfigure(1, weight=1)
        frame_buttons.grid_columnconfigure(2, weight=1)

        ttk.Button(
            frame_buttons,
            text="Save and Update Now", command=parent.end(Result.END, save=True)).grid(
            row=0, column=0, sticky="sew", padx=4, pady=4)
        ttk.Button(
            frame_buttons,
            text="Update Now", command=parent.end(Result.END)).grid(
            row=1, column=0, sticky="sew", padx=4, pady=4)
        ttk.Button(
            frame_buttons,
            text="Save", command=parent.saveSelections).grid(
            row=0, column=1, sticky="sew", padx=4, pady=4)
        ttk.Button(
            frame_buttons, 
            text="Reset", command=parent.resetSelections).grid(
            row=1, column=1, sticky="sew", padx=4, pady=4)
        ttk.Button(
            frame_buttons,
            text="Save and Continue", command=parent.end(Result.NEXT, save=True)).grid(
            row=0, column=2, sticky="sew", padx=4, pady=4)
        ttk.Button(
            frame_buttons,
            text="Continue without Saving", command=parent.end(Result.NEXT, save=False)).grid(
            row=1, column=2, sticky="sew", padx=4, pady=4)

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
