#!/bin/python3

import jfileutil as ju
import gui

import requests
from urllib.request import urlretrieve
from urllib.error import HTTPError, URLError
from os import makedirs, path
from traceback import print_exc, format_exc
from json.decoder import JSONDecodeError
import timeout_decorator
import progressbar
from os import stat
from snip import slow

# Making this extensible to boards like 8chan:
# 1. Make a API mappings file
# 2. Make classes for: Threads, Posts, Chans
# 3. Refactor production code to create objects based on mappings
# 4. Refactor consumption code to read object attributes
# 5. Extend mappings file

# Utility functions and classes


def exec_with_timeout(secs, func, *args, **kwargs):
    """Wrap a function in a timeout. 
    If the function takes longer than `secs` to complete, an exception will be raised.
    
    Args:
        secs (int): Max time until process completion
        func
        *args
        **kwargs
    
    Returns:
        None
    """
    return timeout_decorator.timeout(secs, use_signals=False)(func)(*args)


# Filesystem IO

def loadBoards():
    """Load information about board names from file, handling defaults if needed.
    
    Returns:
        Dict: Key: server, Value: list of board acronyms
    """
    filename = "Boards"
    example = {"4chan": ["wsg", "biz", "gd"]}
    try:
        boards = ju.json_load(filename)
        return boards
    except FileNotFoundError:
        ju.json_save(example, filename)
        print("Missing the boards file. A sample has been generated.")
        print("Please edit the template file in the jobj folder!")
        return example

# Parsing


def trimObj(obj, interest):
    """Remove a set of keys from a dictionary
    
    Args:
        obj (Dict): Description
        interest (List): List of keys to remove
    
    Returns:
        Dict: Filtered version of obj
    """
    pops = []
    for key in obj.keys():
        if key not in interest:
            pops.append(key)
    for key in pops:
        obj.pop(key)
    return obj


def trimThread(thread):
    """Removes unneeded metadata from thread JSON
    
    Args:
        thread (dict): Thread json object
    
    Returns:
        Dict: Trimmed thread json
    """
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


def formatPost(post):
    """Converts a post json to an HTML fragment
    
    Args:
        post (Dict): Post json object
    
    Returns:
        str: HTML representation of post
    """
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


def getThreads(board):
    """Generates trimmed versions of all threads in a board.
    
    Args:
        board (str): Board acronym
    
    Yields:
        Dict: Thread json object
    """
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

# Saving


def saveThreads(board, queue):
    """Process saving of threads in a board. Saves messages and html.
    
    Args:
        board (str): Board acronym
        queue (List): List of thread json objects
    """
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
            ju.json_save(format_exc(), "error_thread_{}f".format(threadno))

        except ConnectionError as e:
            print("Error with thread [{}] {}".format(threadno, threadurl))
            print_exc(limit=1)
            ju.json_save(format_exc(), "error_thread_{}".format(threadno))


def saveImageLog(threadJson, board, sem, verbose=False):
    """Saves all images in a thread, skipping up-to-date images.
    
    Args:
        threadJson 
        board (str): Board acronym
        sem (str): Thread semantic url (text id)
        verbose (bool, optional): Print verbose output
    """
    skips = 0
    threadPosts = threadJson.get("posts")
    realPosts = []
    for post in threadPosts:
        if post.get("ext"):

            (dstdir, dstfile, dstpath) = getDestImagePath(board, sem, post)

            if (path.exists(dstpath)):
                if post.get("fsize") == stat(dstpath).st_size:
                    skips += 1
                    continue
            realPosts.append(post)
    downloadChanImages(board, sem, realPosts)
    if (skips > 0) and verbose:
        print("Skipped {:>3} existing images. ".format(skips))


def saveMessageLog(threadno, sem, threadJson, board):
    """Save text messages to html
    
    Args:
        threadno (int): Thread numerical id
        sem (str): Thread semantic url (text id)
        threadJson
        board (str): Board acronym
    
    Returns:
        TYPE: Description
    """
    msgBase = "./saved/text/{}/".format(board)
    filePath = "{}{s}_{n}.htm".format(msgBase, s=sem, n=threadno)

    try:
        lastPostTime = threadJson.get("posts")[-1].get("time")
        fileUpdateTime = path.getmtime(filePath)
        if fileUpdateTime > lastPostTime:
            return
    except FileNotFoundError:
        pass

    makedirs(msgBase, exist_ok=True)
    with open(filePath, "w", encoding="utf-8") as textfile:
        # print("------> {}".format(filePath))
        for post in threadJson.get("posts"):
            textfile.write(formatPost(post))


def downloadChanImages(board, sem, posts):
    """Downloads images.
    
    Args:
        board (str): Board acronym
        sem (str): Semmantic url (text id)
        posts (list): List of json posts
    
    Returns:
        Returns early if posts is empty.
    """
    if len(posts) == 0:
        print("Nothing to do for thread {board}/{sem}".format(**vars()))
        return
    i = 0
    totalSize = sum([post.get("fsize") for post in posts if post.get("fsize")])
    widgets = [
        "{:30.30}".format(sem),
        ' ', progressbar.Percentage(),
        ' ', progressbar.Bar(),
        ' ', progressbar.FileTransferSpeed(),
        ' ', progressbar.Timer(),
        ' ', progressbar.AdaptiveETA(),
    ]
    pbar = progressbar.ProgressBar(max_value=totalSize, widgets=widgets, redirect_stdout=True)
    for post in slow(posts, 1):
        fsize = post.get("fsize")
        (dstdir, dstfile, dstpath) = getDestImagePath(board, sem, post)

        src = "https://i.4cdn.org/{}/{}{}".format(
            board, post.get("tim"), post.get("ext"))
        downloadFile(src, dstdir, dstfile, debug=post)
        i += fsize
        pbar.update(i)

    pbar.finish()


def getDestImagePath(board, sem, post):
    """Generates paths for saving images

    Returns:
        Tuple (directory, file, path)
    """
    dstdir = "./saved/{}/{}/".format(board, sem)
    dstfile = "{}{}".format(post.get("tim"), post.get("ext"))
    dstpath = path.join(dstdir, dstfile)
    return (dstdir, dstfile, dstpath)


def downloadFile(src, dstdir, dstfile, debug=None, max_retries=5, verbose=False):
    """Download a file from a URL to a destination, with a filename.
    
    Args:
        src (str): URL of source
        dstdir (str): Directory of desination, i.e. C:/Users/Guest/
        dstfile (str): Name of file, i.e. image.jpg
        max_retries (int, optional): Maximum number of times to retry
        verbose (bool, optional): Print additional output
    
    Returns:
        TYPE: Description
    """
    dstpath = "{}{}".format(dstdir, dstfile)
    makedirs(dstdir, exist_ok=True)
    retries = 0

    while (retries < max_retries):
        try:
            exec_with_timeout((5 + 3 * retries), urlretrieve, src, dstpath)
            if verbose:
                print("{} --> {}".format(src, dstpath))
            return dstpath
        except (HTTPError, URLError, ConnectionResetError) as e:
            print("{} -x> {}".format(src, dstpath))
            if verbose:
                print_exc(limit=5)
            else:
                print_exc(limit=2)
        except timeout_decorator.TimeoutError as e:
            if verbose:
                print("{} -x> {} [Timeout]".format(src, dstpath))
        retries += 1
        # print("Retrying [{}/{}]".format(retries, max_retries))


# Main logic


def selectImages(board, preSelectedThreads, saveCallback):
    """Prompt user to select threads to queue
    
    Args:
        board (str): Board acronym
        preSelectedThreads (list): List of thread numbers that were previously selected
        saveCallback (function): Function to save progress to file
    
    Raises:
        KeyboardInterrupt: User canceled process from window
    """
    preSelectionSet = set([thread.get("no") for thread in preSelectedThreads])
    threads = list(getThreads(board))

    # Find 404'd threads
    liveThreadNos = set([thread.get("no") for thread in threads])
    for thread in preSelectedThreads:
        if thread.get("no") not in liveThreadNos:
            print("404: {}".format(thread.get("semantic_url")))

    # Window
    headers = [
        ("no", "ID",),
        ("name", "Author",),
        ("sub", "Subject",),
        ("com", "Comment",),
        # ("time", "Time",),
        ("semantic_url", "URL",),
    ]

    tablerows = [
        {
            'values':
            [
                str(thread.get(h[0])) for h in headers
            ]
        }
        for thread in sorted(threads, key=lambda t: -t.get("no"))
    ]

    def subSaveCallback(selectionIdxs):
        """Summary
        
        Args:
            selectionIdxs (TYPE): Description
        """
        selection = [
            thread
            for thread in threads
            if thread.get("no")
            in selectionIdxs
        ]
        saveCallback(selection)

    SW = gui.SelectorWindow(
        "/{}/ threads".format(board),
        [h[1] for h in headers],
        tablerows,
        preSelectionSet,
        subSaveCallback
    )

    # Break out of a higher loop
    if SW.RESULT == gui.Result.END:
        raise KeyboardInterrupt("Canceled")

    if SW.RESULT == gui.Result.ABORT:
        from os import abort
        abort()

    return


def main():

    # Load
    boards = loadBoards().get("4chan")
    try:
        downloadQueue = ju.json_load("downloadQueue")
    except FileNotFoundError:
        downloadQueue = {}

    # Get selections
    try:
        for board in boards:
            oldSelection = (downloadQueue.get(board) or [])
            downloadQueue[board] = oldSelection  # Fallback

            def saveCallback(selection):
                """Summary
                
                Args:
                    selection (TYPE): Description
                """
                downloadQueue[board] = selection
                ju.json_save(downloadQueue, "downloadQueue")
                print("Saved to file")

            selectImages(board, oldSelection, saveCallback)

    except KeyboardInterrupt:
        print("Selections canceled, jumping straight to downloading threads. ")
        ju.json_save(downloadQueue, "downloadQueue")
        print("Saved to file")

    # Run downloads
    for board in list(downloadQueue.keys()):
        queueList = downloadQueue.get(board)
        saveThreads(board, queueList)


if __name__ == "__main__":
    main()
