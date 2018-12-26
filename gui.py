import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont


class SelectorWindow(tk.Tk):
    def __init__(self, title, items, selections, *args, **kwargs):
        super(SelectorWindow, self).__init__(*args, **kwargs)

        self.cancel = False
        self.selections = selections

        self.protocol("WM_DELETE_WINDOW", self.cmd_cancel)
        self.bind("<Escape>", self.cmd_done)

        self.SelectorFrame = SelectorFrame(self, title, items, selections)
        self.SelectorFrame.grid(row=8, column=8)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.geometry("600x800")

        self.mainloop()

    def cmd_cancel(self, event=None):
        self.cancel = True
        self.destroy()

    def cmd_done(self, event=None):
        self.selections = self.SelectorFrame.getSelections()
        self.destroy()


class SelectorFrame(tk.Frame):

    # Init and window management
    def __init__(self, parent, title, items, selections, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)

        # Setup GUI parts
        lab_title = lab_title = tk.Label(text=title, font=("Helvetica", 24))
        lab_title.grid(row=0, column=0, sticky=tk.W + tk.E)

        scrollbar = tk.Scrollbar()
        scrollbar.grid(
            row=1, column=0, sticky=tk.N + tk.S + tk.E)

        listbox_threads = tk.Listbox(relief=tk.GROOVE, selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set)
        listbox_threads.grid(
            row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=(4, 18))

        scrollbar.config(command=listbox_threads.yview)

        # Buttons, in a frame
        frame_buttons = tk.Frame()
        frame_buttons.grid(row=2, column=0, sticky="sew")

        # Space buttons evenly
        frame_buttons.grid_columnconfigure(0, weight=1)
        frame_buttons.grid_columnconfigure(1, weight=1)

        btn_done = tk.Button(master=frame_buttons, text="Next", command=parent.cmd_done)
        btn_done.grid(row=0, column=1, sticky="sew", padx=4, pady=4)

        btn_cancel = tk.Button(frame_buttons, text="Update Now", command=parent.cmd_cancel)
        btn_cancel.grid(row=0, column=0, sticky="sew", padx=4, pady=4)

        # Expose interfaces
        self.listbox_threads = listbox_threads

        # Load data
        self.loadItems(items, selections)

    def loadItems(self, items, selections):
        for val in items:
            self.listbox_threads.insert(
                tk.END, val)

        for index in selections:
            self.listbox_threads.selection_set(index)

    def getSelections(self):
        return self.listbox_threads.curselection()


class MultiColumnListbox(tk.Frame):
    """use a ttk.TreeView as a multicolumn ListBox"""

    def __init__(self, parent, headers, tabledata, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.tree = None
        self.headers = headers  # This must remain static.
        self.setup_widgets(headers)
        self._build_tree(headers, tabledata)

    def setup_widgets(self, headers):
        container = tk.Frame()
        container.pack(fill='both', expand=True)

        # Create a treeview with dual scrollbars
        self.tree = ttk.Treeview(columns=headers, show="headings")
        vsb = ttk.Scrollbar(orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky='nsew', in_=container)
        vsb.grid(column=1, row=0, sticky='ns', in_=container)
        hsb.grid(column=0, row=1, sticky='ew', in_=container)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def sortby(self, tree, col, descending):
        """sort tree contents when a column header is clicked on"""
        # grab values to sort
        data = [(tree.set(child, col), child) for child in tree.get_children('')]
        # if the data to be sorted is numeric change to float
        # data =  change_numeric(data)
        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        # switch the heading so it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, int(not descending)))

    def _build_tree(self, headers, itemlist):
        for col in headers:
            # Use this for sortable columns.
            # self.tree.heading(col, text=col.title(), command=lambda c=col: self.sortby(self.tree, c, 0))
            self.tree.heading(col, text=col.title())
            # adjust the column's width to the header string
            self.tree.column(col, width=tkFont.Font().measure(col.title()))

        for item in itemlist:
            self.tree.insert('', tk.END, values=item)
            # adjust column's width if necessary to fit each value
            for ix, val in enumerate(item):
                col_w = tkFont.Font().measure(val)
                if self.tree.column(headers[ix], width=None) < col_w:
                    self.tree.column(headers[ix], width=col_w)
