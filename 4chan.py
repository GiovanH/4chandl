#!/bin/python3

import jfileutil as ju

import requests
from urllib.request import urlretrieve
from urllib.error import HTTPError
from os import makedirs, path
from traceback import print_exc
from json.decoder import JSONDecodeError
import tkinter as tk
import html.parser


class SelectorWindow():

    # Init and window management
    def __init__(self, Tk, title, items, selections):
        self.main = Tk
        self.selections = selections
        self.cancel = False

        self.lab_title = tk.Label(
            self.main, text=title, font=("Helvetica", 24))
        self.lab_title.grid(row=0, column=0, sticky=tk.W + tk.E, columnspan=2)

        self.scrollbar = tk.Scrollbar(self.main)
        self.scrollbar.grid(
            row=1, column=1, sticky=tk.N + tk.S + tk.E)

        self.listbox_threads = tk.Listbox(
            self.main, relief=tk.GROOVE, selectmode=tk.MULTIPLE, yscrollcommand=self.scrollbar.set)
        self.listbox_threads.grid(
            row=1, column=0, sticky=tk.N + tk.S + tk.E + tk.W, padx=(4, 18), columnspan=2)

        self.btn_cancel = tk.Button(
            self.main, text="Update Now", command=self.cmd_cancel)
        self.btn_cancel.grid(
            row=2, column=0, sticky=tk.W + tk.E, padx=4, pady=4)

        self.btn_done = tk.Button(
            self.main, text="Next", command=self.cmd_done)
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


        self.scrollbar.config( command = self.listbox_threads.yview )

    def cmd_cancel(self, event=None):
        self.cancel = True
        self.main.destroy()

    def cmd_done(self, event=None):
        self.selections = self.listbox_threads.curselection()
        self.main.destroy()


class HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super(HTMLTextExtractor, self).__init__()
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def get_text(self):
        return ''.join(self.result)


def html_to_text(html):
    s = HTMLTextExtractor()
    s.feed(html)
    return s.get_text()


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
    sub = thread.get("sub")
    com = thread.get("com")
    sem = thread.get("semantic_url")
    auth = thread.get("name")
    
    tname = ""
    if sub:
        tname += "[{}] ".format(sub)
    if com:
        tname += "{} ".format(html_to_text(com))
    if sem:
        tname += "/{} ".format(sem)
    tname += " ~{}".format(auth)

    return tname


def selectImages(board, preSelectedThreads):
    selectedSet = set([thread.get("no") for thread in preSelectedThreads])
    threads = list(getThreads(board))
    threads = sorted(threads, key=lambda t: -t.get("no"))

    # Write selectionIndices
    selectionIndices = []
    for i in range(0, len(threads)):
        if threads[i].get("no") in selectedSet:
            selectionIndices.append(i)

    # Find 404'd threads
    liveThreadNos = set([thread.get("no") for thread in threads])
    for thread in preSelectedThreads:
        if thread.get("no") not in liveThreadNos:
            print("404: {}".format(friendlyThreadName(thread)[:64]))

    friendlyNames = [friendlyThreadName(thread) for thread in threads]

    # print("selectedSet: {}".format(selectedSet))
    # print("selectionIndices: {}".format(selectionIndices))

    # Window
    Tk = tk.Tk()
    SW = SelectorWindow(Tk, "/{}/ threads".format(board), friendlyNames, selectionIndices)
    Tk.mainloop()

    # Break out of a higher loop
    if SW.cancel:
        raise KeyboardInterrupt("Canceled")

    # Indices to thread objects
    selection = [threads[i] for i in SW.selections]
    # print("selections: {}".format(SW.selections))
    return selection


def saveThreads(board, queue):
    for thread in queue:
        threadno = thread.get("no")
        threadurl = "https://a.4cdn.org/{}/thread/{}.json".format(board, threadno)
        try:
            # Get thread data
            threadJson = requests.get(threadurl).json()
            sem = threadJson.get("posts")[0].get("semantic_url")

            # Run thread operations
            saveMessageLog(threadno, sem, threadJson, board)
            saveImageLog(threadJson, board, sem)

        except JSONDecodeError as e:
            print("Error with thread [{}] {}".format(threadno, threadurl))
            print_exc(limit=1)
            ju.json_save(thread, "error_thread_{}".format(threadno))


def saveImageLog(threadJson, board, sem):
    skips = 0   
    for post in threadJson.get("posts"):
        if post.get("ext"):
            try:
                download4chanImage(board, sem, post)
            except FileExistsError:
                skips += 1
    if (skips > 0):
        print("Skipped {:>3} existing images. ".format(skips))


def saveMessageLog(threadno, sem, threadJson, board):
    msgBase = "./saved/text/{}/".format(board)
    filePath = "{}{}_{}.htm".format(msgBase, threadno, sem)

    try:
        lastPostTime = threadJson.get("posts")[-1].get("time")
        fileUpdateTime = path.getmtime(filePath)
        if fileUpdateTime > lastPostTime:
            return
    except FileNotFoundError:
        pass

    makedirs(msgBase, exist_ok=True)
    with open(filePath, "w", encoding="utf-8") as textfile:
        print("-----> {}".format(filePath))
        for post in threadJson.get("posts"):
            textfile.write(formatPost(post))


def formatPost(post):
    subfields = ["sub", "name", "now", "no"]
    subline = " ".join([str(post.get(field))
                        for field in subfields if post.get(field) is not None])
    return "\
    <div class='post'><span class='subline' id='p{no}'>>{subline} >>{no}</span>\n \
    <span class='file'>File: {file}</span>\n \
    {com}</div>".format(
        subline=subline,
        no=post.get("no"),
        file=(post.get("filename") + post.get("ext")
              if post.get("filename") else "None"),
        com=(("\n<p>" + post.get("com") + "</p>") if post.get("com") else "")
    )


def download4chanImage(board, sem, post):
    dstdir = "./saved/{}/{}/".format(board, sem)
    dstfile = "{}{}".format(post.get("tim"), post.get("ext"))

    if (path.exists("{}{}".format(dstdir, dstfile))):
        raise FileExistsError(dstfile)

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
        ju.json_save(downloadQueue, "downloadQueue")
    except KeyboardInterrupt:
        print("Program canceled, jumping straight to downloading threads. ")

    # Run downloads
    for board in list(downloadQueue.keys()):
        queueList = downloadQueue.get(board)
        saveThreads(board, queueList)


if __name__ == "__main__":
    main()
