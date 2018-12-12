#!/bin/python3

import jfileutil as ju

import requests
from urllib.request import urlretrieve
from urllib.error import HTTPError
from os import makedirs, path
from traceback import print_exc
from json.decoder import JSONDecodeError
import tkinter as tk


class SelectorWindow():

    # Init and window management
    def __init__(self, Tk, title, items, selections):
        self.main = Tk
        self.selections = selections
        self.cancel = False

        self.lab_title = tk.Label(self.main, text=title, font=("Helvetica", 24))
        self.lab_title.grid(row=0, column=0, sticky=tk.W + tk.E, columnspan=2)

        self.listbox_threads = tk.Listbox(
            self.main, relief=tk.GROOVE, selectmode=tk.MULTIPLE)
        self.listbox_threads.grid(
            row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=4, columnspan=2)

        self.btn_cancel = tk.Button(
            self.main, text="Skip to DL", command=self.cmd_cancel)
        self.btn_cancel.grid(row=2, column=0, sticky=tk.W + tk.E, padx=4, pady=4)

        self.btn_done = tk.Button(
            self.main, text="Save and Continue", command=self.cmd_done)
        self.btn_done.grid(row=2, column=1, sticky=tk.W + tk.E, padx=4, pady=4)

        top = self.main.winfo_toplevel()
        top.bind("<Escape>", self.cmd_done)
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)
        top.rowconfigure(1, weight=1)
        top.geometry("300x800")

        for val in items:
            self.listbox_threads.insert(
                tk.END, val)

        for index in selections:
            self.listbox_threads.selection_set(index)

    def cmd_cancel(self, event=None):
        self.cancel = True
        self.main.destroy()

    def cmd_done(self, event=None):
        self.selections = self.listbox_threads.curselection()
        print("TK Selections after: {}".format(self.selections))
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
        print("Please edit the template file in the jobj folder!")
        return example


def trimObj(obj, interest):
    pops = []
    for key in obj.keys():
        if key not in interest:
            pops.append(key)
    for key in pops:
        obj.pop(key)
    return obj


def trimThread(thread):
    interest = [
        "no", 
        "name", 
        "sub", 
        "com", 
        "tim", 
        "archived", 
        "semantic_url",
        "tag"
    ]
    return trimObj(thread, interest)


def getThreads(board):
    catalog = requests.get("https://a.4cdn.org/{}/{}.json".format(board, "catalog")).json()
    # ju.json_save(catalog, "catalog_{}".format(board))
    for page in catalog:
        for thread in page.get("threads"):
            yield trimThread(thread)


def friendlyThreadName(thread):
    name = thread.get("sub") or thread.get("com") or thread.get("semantic_url") or thread.get("name")
    return name[:64]


def selectImages(board, preSelectedThreads):
    selectedSet = set([thread.get("no") for thread in preSelectedThreads])
    threads = list(getThreads(board))

    # Write selectionIndices
    selectionIndices = []
    for i in range(0, len(threads)):
        if threads[i].get("no") in selectedSet:
            selectionIndices.append(i)

    # Find 404'd threads
    liveThreadNos = set([thread.get("no") for thread in threads])
    for thread in preSelectedThreads:
        if thread.get("no") not in liveThreadNos:
            print("Thread {} has 404'd, removing. ".format(friendlyThreadName(thread)))

    friendlyNames = [friendlyThreadName(thread) for thread in threads]

    # Window
    Tk = tk.Tk()
    SW = SelectorWindow(Tk, "/{}/ threads".format(board), friendlyNames, selectionIndices)
    Tk.mainloop()

    if SW.cancel:
        raise KeyboardInterrupt("Canceled")

    # Indices to thread objects
    selection = [threads[i] for i in SW.selections]
    return selection


def saveThreads(board, queue):
    for thread in queue:

        threadno = thread.get("no")
        threadurl = "https://a.4cdn.org/{}/thread/{}.json".format(board, threadno)
        try:
            threadJson = requests.get(threadurl).json()
            sem = threadJson.get("posts")[0].get("semantic_url")

            for post in threadJson.get("posts"):
                if post.get("ext"):
                    download4chanImage(board, sem, post)
        except JSONDecodeError as e:
            print("Error with thread [{}] {}".format(threadno, threadurl))
            print_exc(limit=1)
            ju.json_save(thread, "error_thread_{}".format(threadno))


skips = 0


def download4chanImage(board, sem, post):
    dstdir = "./saved/{}/{}/".format(board, sem)
    dstfile = "{}{}".format(post.get("tim"), post.get("ext"))

    # Fun with skips
    global skips
    if (path.exists("{}{}".format(dstdir, dstfile))):
        skips += 1
        return
    else:
        if (skips > 0):
            print("Skipped {} existing files. ".format(skips))
            skips = 0

    src = "https://i.4cdn.org/{}/{}{}".format(
        board, post.get("tim"), post.get("ext"))
    downloadFile(src, dstdir, dstfile, debug=post)


def downloadFile(src, dstdir, dstfile, debug=None):
    dstpath = "{}{}".format(dstdir, dstfile)
    makedirs(dstdir, exist_ok=True)
    try:
        urlretrieve(src, dstpath)
        print("{} --> {}".format(src, dstpath))
    except HTTPError:
        print("{} -x> {}".format(src, dstpath))
        print_exc(limit=1)
        ju.json_save(debug, "error_download_{}".format(dstfile))


# TODO: Save the queue to a file, so we can resume an interupted session. 

def main():
    # Load
    boards = loadBoards()
    try:
        downloadQueue = ju.json_load("downloadQueue")
    except FileNotFoundError:
        downloadQueue = {}

    # Get selections
    try:
        for board in boards:
            oldSelection = (downloadQueue.get(board) or [])
            downloadQueue[board] = oldSelection  # Fallback
            selection = selectImages(board, oldSelection)
            downloadQueue[board] = selection
    except KeyboardInterrupt:
        print("Program canceled, discarding unsaved changes, but downloading old threads. ")

        ju.json_save(downloadQueue, "downloadQueue")

    # Run downloads
    for board in list(downloadQueue.keys()):
        queueList = downloadQueue.get(board)
        saveThreads(board, queueList)


if __name__ == "__main__":
    main()
