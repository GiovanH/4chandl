#!/bin/python3
from distutils.dir_util import copy_tree
from glob import glob
from os.path import abspath, normpath, dirname, split, join, getmtime
from send2trash import send2trash
# from time import sleep
import os
# from traceback import print_exc
import datetime
from snip import loom

import prompt_toolkit as ptk


def renameDir(src, dst):
    # jobstr = "{} -> {}".format(src, dst)
    if abspath(dst.lower()) == abspath(src.lower()):
        # print("Same folder.")
        return
    try:
        copy_tree(src, dst)
        send2trash(src)
        # print(jobstr)
        return
    except Exception as e:
        print(e)
        raise


sortmethods = {
    "modtime": lambda g, r: sorted(g, key=getmtime, reverse=r),
    "length": lambda g, r: sorted(g, key=len, reverse=r),
    "filecount": lambda g, r: sorted(g, key=lambda x: len(glob(join(x, "*"))), reverse=r),
    "alpha": lambda g, r: sorted(g, reverse=r)
}


def getArgs():
    import argparse
    ap = argparse.ArgumentParser()
    defsrcglob = join("saved", "*", "*", "")
    ap.add_argument("-s", "--srcglob", default=defsrcglob,
                    help="From where to pull folders. Default is `{}`".format(defsrcglob))
    ap.add_argument("-d", "--destfldr", default=None,
                    help="Root directory for new folders")
    ap.add_argument("--sort", default="modtime",
                    help="Method to sort directories")
    ap.add_argument("--mock", action="store_true",
                    help="Don't actually perform disk operations")
    ap.add_argument("-r", "--reverse", action="store_true",
                    help="Reverse sort")
    ap.add_argument("--use-completer", action="store_true",
                    help="Use path completer")
    return ap.parse_args()


def PathCompleter(destfldr):
    globstr = join(destfldr, "**", "")
    print("Scanning paths in", globstr)
    paths = [
        root.replace(destfldr, "").replace("\\", "/") + "/"
        for root, dirs, files in os.walk(destfldr)
    ]
    paths = [p[1:] if p.startswith("/") else p for p in paths]

    # print(paths)
    return ptk.completion.WordCompleter(paths, ignore_case=True, match_middle=False, sentence=r"[. ]+")


def main():
    args = getArgs()

    srcdir = args.srcglob  # abspath(args.srcglob)  # .replace("/", sep)

    if args.mock:
        print("Mock is ON.")

    def getdestfldr(path):
        destfldr = abspath(args.destfldr) if args.destfldr else None
        if not destfldr:
            return dirname(path)
        else:
            return destfldr

    print("Source:", srcdir)
    print("Dest:", getdestfldr("$src/"))

    path_completer = PathCompleter(getdestfldr("$src/")) if args.use_completer else None

    globbed = glob(srcdir)
    try:
        globbed = sortmethods[args.sort](globbed, args.reverse)
        # print(globbed)
    except KeyError:
        print("No such method as", args.sort)
        print("Valid methods include", sortmethods.keys())
    with loom.Spool(6) as spool:
        for path in globbed:

            print(datetime.datetime.fromtimestamp(getmtime(path)).strftime("%Y-%m-%d"), normpath(path))
            try:
                ans = ptk.prompt(
                    "New path? > ", 
                    bottom_toolbar=lambda: str(spool), reserve_space_for_menu=20,
                    completer=path_completer, complete_in_thread=True)
            except EOFError:
                ans = '\x04'
            except KeyboardInterrupt:
                print("Interrupt.")
                # spool.finish(verbose=True)
                break

            try:
                if ans == "":
                    continue

                ans = split(normpath(path))[1] if ans == '\x04' else ans  # ^D
                newDir = join(getdestfldr(path), ans)
                print("{} -> {}".format(path, newDir))
                if not args.mock:
                    spool.enqueue(name=ans, target=renameDir, args=(path, newDir,))
            except ValueError:
                print("Invalid input. ")

        print("Finishing")
        spool.finish()
        assert len(spool.queue) == 0, "spool did not finish"
        return 0


if __name__ == "__main__":
    main()
