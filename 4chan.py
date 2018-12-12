#!/bin/python3

import jfileutil as ju

import requests
from urllib.request import urlretrieve
from os import makedirs, path

import tkinter as tk


class SelectorWindow():

    # Init and window management
    def __init__(self, Tk, title, items, selections):
        self.main = Tk
        self.selections = selections

        self.lab_title = tk.Label(self.main, text=title, font=("Helvetica", 24))
        self.lab_title.grid(row=0, column=0, sticky=tk.W + tk.E)

        self.listbox_threads = tk.Listbox(
            self.main, relief=tk.GROOVE, selectmode=tk.MULTIPLE)
        self.listbox_threads.grid(
            row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=4)

        self.btn_done = tk.Button(
            self.main, text="Open", takefocus=False, command=self.cmd_done)
        self.btn_done.grid(row=2, column=0, sticky=tk.W + tk.E, padx=4, pady=4)

        top = self.main.winfo_toplevel()
        top.bind("<Escape>", self.cmd_done)
        top.columnconfigure(0, weight=1)
        top.rowconfigure(1, weight=1)
        top.geometry("300x800")

        for val in items:
            self.listbox_threads.insert(
                tk.END, val)

        for index in selections:
            self.listbox_threads.selection_set(index)

    def cmd_done(self, event=None):
        self.selections = self.listbox_threads.curselection()
        self.main.destroy()


def loadBoards():
    filename = "4chanBoards"
    example = ["wsg", "biz", "gd"]
    try:
        boards = ju.json_load(filename)
        return boards
    except FileNotFoundError:
        ju.json_save(example, filename)
        print("Missing the boards file. A sample has been generated.")
        return example


def getThreads(board):
    def grab(b, t):
        return requests.get("https://a.4cdn.org/{}/{}.json".format(b, t)).json()
    catalog = grab(board, "catalog")
    # ju.json_save(catalog, "catalog_{}".format(board))
    for page in catalog:
        for thread in page.get("threads"):
            yield thread


def selectImages(board, preSelectedThreads):
    selectionIndices = []

    selectedSet = set([thread.get("no") for thread in preSelectedThreads])
    print(selectedSet)

    threads = list(getThreads(board))

    for i in range(0, len(threads)):
        if threads[i].get("no") in selectedSet:
            selectionIndices.append(i)

    print(selectionIndices)
    # friendlyNames = ["{}: {}".format(
    #     thread.get("semantic_url"),
    friendlyNames = ["{}".format(
        thread.get("sub") or thread.get("com") or thread.get("name"))
        for thread in threads]

    Tk = tk.Tk()
    SelectorWindow(Tk, "/{}/ threads".format(board), friendlyNames, selectionIndices)
    Tk.mainloop()

    selection = [threads[i] for i in selectionIndices]
    return selection


def saveThreads(board, queue):
    for thread in queue:

        threadno = thread.get("no")
        threadJson = requests.get(
            "https://a.4cdn.org/{}/thread/{}.json".format(board, threadno)).json()
        # ju.json_save(threadJson, "thread_{}".format(threadno))

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


# TODO: Save the queue to a file, so we can resume an interupted session. 

def main():
    boards = loadBoards()
    try:
        downloadQueue = ju.json_load("downloadQueue")
    except FileNotFoundError:
        downloadQueue = {}

    for board in boards:
        downloadQueue[board] = selectImages(board, downloadQueue[board])

    for board in list(downloadQueue.keys()):
        ju.json_save(downloadQueue, "downloadQueue")
        # queueList = downloadQueue.pop(board)
        queueList = downloadQueue.get(board)
        saveThreads(board, queueList)
        # TODO: Detect 404s


if __name__ == "__main__":
    main()
