#!/bin/python3

import jfileutil as ju

import requests
from urllib.request import urlretrieve
from os import makedirs, path

import tkinter as tk


class SelectorWindow():

    # Init and window management
    def __init__(self, Tk, items, selection):
        self.main = Tk
        self.selection = selection

        self.listbox_context = tk.Listbox(
            self.main, relief=tk.GROOVE, selectmode=tk.MULTIPLE)
        self.listbox_context.grid(
            row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

        self.btn_done = tk.Button(
            self.main, text="Open", takefocus=False, command=self.cmd_done)
        self.btn_done.grid(row=1, column=0, sticky=tk.W)

        top = self.main.winfo_toplevel()
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        for val in items:
            self.listbox_context.insert(
                tk.END, val)

    def cmd_done(self):
        self.selection += self.listbox_context.curselection()
        self.main.destroy()


def loadBoards():
    filename = "4chanBoards"
    example = []
    try:
        boards = ju.json_load(filename)
        return boards
    except FileNotFoundError:
        ju.json_save(example, filename)
        print("Missing the boards file. A sample has been generated.")
        raise


def getThreads(board):
    def grab(b, t):
        return requests.get("https://a.4cdn.org/{}/{}.json".format(b, t)).json()
    catalog = grab(board, "catalog")
    ju.json_save(catalog, "catalog_{}".format(board))
    for page in catalog:
        for thread in page.get("threads"):
            yield thread


def selectImages(board):
    selectionIndices = []

    threads = list(getThreads(board))
    # friendlyNames = ["{}: {}".format(
    #     thread.get("semantic_url"),
    friendlyNames = ["{}".format(
        thread.get("sub") or thread.get("com") or thread.get("name"))
        for thread in threads]

    Tk = tk.Tk()
    SelectorWindow(Tk, (friendlyNames), selectionIndices)
    Tk.mainloop()

    selection = [threads[i] for i in selectionIndices]
    return selection


def saveThreads(board, queue):
    for thread in queue:

        threadno = thread.get("no")
        threadJson = requests.get(
            "https://a.4cdn.org/{}/thread/{}.json".format(board, threadno)).json()
        ju.json_save(threadJson, "thread_{}".format(threadno))

        sem = threadJson.get("posts")[0].get("semantic_url")

        for post in threadJson.get("posts"):
            if post.get("ext"):
                download4chanImage(board, sem, post)


def download4chanImage(board, sem, post):
    dstdir = "./saved/{}/{}/".format(board, sem)
    dstfile = "{}{}{}".format(dstdir, post.get("tim"), post.get("ext"))
    if (path.exists(dstfile)):
        return

    src = "https://i.4cdn.org/{}/{}{}".format(
        board, post.get("tim"), post.get("ext"))

    print("{} --> {}".format(src, dstfile))
    makedirs(dstdir, exist_ok=True)
    urlretrieve(src, dstfile)


def main():
    boards = loadBoards()
    downloadQueue = {}
    for board in boards:
        downloadQueue[board] = []
        downloadQueue[board] += selectImages(board)
    for board in downloadQueue.keys():
        saveThreads(board, downloadQueue[board])


if __name__ == "__main__":
    main()
