#!/bin/python3
from distutils.dir_util import copy_tree
from glob import glob
from os.path import *
from send2trash import send2trash
# from time import sleep
# from traceback import print_exc
import datetime
import loom


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
    "modtime": lambda g: sorted(g, key=getmtime),
    "length": lambda g: sorted(g, key=len),
    "filecount": lambda g: sorted(g, key=lambda x: len(glob(x))),
    "alpha": lambda g: sorted(g)
}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--srcglob", default="./saved/*/*/",
                    help="From where to pull folders. Default is `./saved/*/*/` ")
    ap.add_argument("-d", "--destfldr", default=None,
                    help="Root directory for new folders")
    ap.add_argument("--sort", default="modtime",
                    help="Method to sort directories")
    args = ap.parse_args()

    srcdir = args.srcglob  # abspath(args.srcglob)  # .replace("/", sep)
    destfldr = abspath(args.destfldr) if args.destfldr else None

    def getdestfldr():
        if not destfldr:
            return split(dirname(path))[0]
        else:
            return destfldr

    print("Source:", srcdir)
    globbed = glob(srcdir)
    try:
        globbed = sortmethods[args.sort](globbed)
    except KeyError:
        print("No such method as", args.sort)
        print("Valid methods include", sortmethods.keys())
    with loom.Spool(6) as spool:
        for path in globbed:
            print(datetime.datetime.fromtimestamp(getmtime(path)).strftime("%Y-%m-%d"), relpath(path))
            try:
                ans = input("New name? > ")
            except EOFError as e:
                ans = '\x04'
            try:
                if ans == "":
                    continue
                ans = abspath(ans)
                ans = split(relpath(path))[1] if ans == '\x04' else ans  # ^D
                newDir = join(getdestfldr(), ans)
                print("{} -> {}".format(path, newDir))
                spool.enqueue(name=ans, target=renameDir, args=(path, newDir,))
            except ValueError:
                print("Invalid input. ")
        print("Finishing")


def run():
    try:
        main()
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    run()
