#!/bin/python3

import jfileutil as ju
import gui

import requests
from urllib.request import urlretrieve
from urllib.error import HTTPError, URLError
from os import makedirs, path
from traceback import print_exc
from json.decoder import JSONDecodeError
import timeout_decorator
import progressbar

import html.parser


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
        "time",
        "archived",
        "semantic_url",
        "tag"
    ]
    return trimObj(thread, interest)


def getThreads(board):
    try:
        catalog = requests.get("https://a.4cdn.org/{}/{}.json".format(board, "catalog"))
        if not catalog.ok:
            catalog.raise_for_status()
        catalog = catalog.json()
    except JSONDecodeError as e:
        print(catalog)
        raise
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

    # Find 404'd threads
    liveThreadNos = set([thread.get("no") for thread in threads])
    for thread in preSelectedThreads:
        if thread.get("no") not in liveThreadNos:
            print("404: {}".format(friendlyThreadName(thread)[:64]))

    # Window
    SW = gui.SelectorWindow(board, threads, selectedSet)

    # Break out of a higher loop
    if SW.cancel:
        raise KeyboardInterrupt("Canceled")

    # Indices to thread objects
    selection = [thread for thread in threads if thread.get("no") in SW.selections]
    
    # print("selections: {}".format(SW.selections))
    return selection


def saveThreads(board, queue):
    pbar = progressbar.ProgressBar(max_value=len(queue), redirect_stdout=True)
    i = 0
    for thread in queue:
        i += 1
        pbar.update(i)

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
    pbar.finish()


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
        print("------> {}".format(filePath))
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


def exec_with_timeout(secs, func, *args, **kwargs):
    return timeout_decorator.timeout(secs, use_signals=False)(func)(*args)


def downloadFile(src, dstdir, dstfile, debug=None, max_retries=6):
    dstpath = "{}{}".format(dstdir, dstfile)
    makedirs(dstdir, exist_ok=True)
    retries = 0

    while (retries < max_retries):
        try:
            exec_with_timeout(8, urlretrieve, src, dstpath)
            print("{} --> {}".format(src, dstpath))
        except Exception:
            print("{} -x> {}".format(src, dstpath))
            print_exc(limit=3)
            ju.json_save(debug, "error_download_{}".format(dstfile))
            retries += 1


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
        print("Selections canceled, jumping straight to downloading threads. ")

    # Run downloads
    for board in list(downloadQueue.keys()):
        queueList = downloadQueue.get(board)
        saveThreads(board, queueList)


if __name__ == "__main__":
    main()
