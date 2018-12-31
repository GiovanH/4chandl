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
        
        listbox_threads = MultiColumnListbox(self, headers, items, multiselect=True, hscroll=True)
        listbox_threads.grid(row=1, column=0, sticky="nsew", padx=(4, 18))

        # Buttons, in a frame
        frame_buttons = tk.Frame(self)
        frame_buttons.grid(row=2, column=0, sticky="sew")

        # Space buttons evenly
        frame_buttons.grid_columnconfigure(0, weight=1)
        frame_buttons.grid_columnconfigure(1, weight=1)

        btn_done = tk.Button(frame_buttons, text="Save and Continue", command=parent.cmd_done)
        btn_done.grid(row=0, column=1, sticky="sew", padx=4, pady=4)

        btn_cancel = tk.Button(frame_buttons, text="Save and Update", command=parent.cmd_cancel)
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


class MultiColumnListbox(tk.Frame):
    """use a ttk.TreeView as a multicolumn ListBox"""

    def __init__(self, parent, headers, tabledata, multiselect=False, sortable=True, vscroll=True, hscroll=False, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.tree = None
        self.sortable = sortable
        self.headers = headers  # This must remain static.

        self.temporary_items = []

        self.setup_widgets(headers, vscroll=vscroll, hscroll=hscroll)
        self.build_tree(headers, tabledata)

        if multiselect:
            self.tree.configure(selectmode=tk.NONE)
            self.tree.bind("<Button-1>", self.handle_multiselect_click)

    def handle_multiselect_click(self, event):
        item = self.tree.identify('item', event.x, event.y)
        self.tree.selection_toggle(item)

    def setup_widgets(self, headers, vscroll=True, hscroll=True):
        container = self

        # Create a treeview with dual scrollbars
        self.tree = ttk.Treeview(self, columns=headers, selectmode=tk.EXTENDED, show="headings")
        self.tree.grid(column=0, row=0, sticky='nsew', in_=container)

        if vscroll:
            vsb = ttk.Scrollbar(orient="vertical", command=self.tree.yview)
            vsb.grid(column=1, row=0, sticky='ns', in_=container)
            self.tree.configure(yscrollcommand=vsb.set)
        if hscroll:
            hsb = ttk.Scrollbar(orient="horizontal", command=self.tree.xview)
            hsb.grid(column=0, row=1, sticky='ew', in_=container)
            self.tree.configure(xscrollcommand=hsb.set)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def sortby(self, tree, col, descending):
        """sort tree contents when a column header is clicked on"""

        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        # if the data to be sorted is numeric change to float
        # data =  change_numeric(data)

        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)

        # switch the heading so it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, int(not descending)))

    def build_tree(self, headers, itemlist, resize=True):
        for col in headers:
            if self.sortable:
                self.tree.heading(col, text=col.title(), command=lambda c=col: self.sortby(self.tree, c, 0))
            else:
                self.tree.heading(col, text=col.title())
            if resize:
                # adjust the column's width to the header string
                self.tree.column(col, width=tkFont.Font().measure(col.title()))

        if resize:
            # Super dirty average
            avgs = [0] * len(headers)

            for item in itemlist:
                newitem = self.tree.insert('', tk.END, values=item)
                self.temporary_items.append(newitem)

                # adjust column's width if necessary to fit each value
                for ix, val in enumerate(item):
                    if str(val) != str(None):
                        col_w = tkFont.Font().measure(val)
                        avgs[ix] = (col_w + avgs[ix]) / 2  

            for i in range(0, len(headers)):
                self.tree.column(headers[i], width=min(int(avgs[i]), 480))
        else:
            for item in itemlist:
                newitem = self.tree.insert('', tk.END, values=item)
                self.temporary_items.append(newitem)

    def update_tree(self, itemlist, resize=True):
        self.tree.delete(*self.tree.get_children())
        for item in itemlist:
            self.tree.insert('', tk.END, values=item)

    def modSelection(self, selectionNos):
        select_these_items = [
            child for child in self.tree.get_children('')
            if int(self.tree.set(child, "ID")) in selectionNos
        ]
        self.tree.selection_set(select_these_items)
        # self.tree.selection_set()

    def getSelections(self):
        return [int(self.tree.set(child, "ID")) for child in self.tree.selection()]
