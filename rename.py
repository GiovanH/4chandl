#!/bin/python3
from distutils.dir_util import copy_tree
from glob import glob
from os.path import abspath, relpath, dirname, split, join, getmtime
from send2trash import send2trash
# from time import sleep
# from traceback import print_exc
import datetime
from snip import loom


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
    "filecount": lambda g: sorted(g, key=lambda x: len(glob(join(x, "*")))),
    "alpha": lambda g: sorted(g)
}


def main():
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
    args = ap.parse_args()

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
    globbed = glob(srcdir)
    try:
        globbed = sortmethods[args.sort](globbed)
        # print(globbed)
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
            except KeyboardInterrupt:
                print("Interrupt.")
                # spool.finish(verbose=True)
                break

            try:
                if ans == "":
                    continue
                if ans == '\x18':
                    spool.finish(verbose=True, use_pbar=True)
                    return 0
                # ans = abspath(ans)
                ans = split(relpath(path))[1] if ans == '\x04' else ans  # ^D
                newDir = join(getdestfldr(path), ans)
                print("{} -> {}".format(path, newDir))
                if not args.mock:
                    spool.enqueue(name=ans, target=renameDir, args=(path, newDir,))
            except ValueError:
                print("Invalid input. ")
        print("Finishing")
        spool.finish(verbose=True, use_pbar=True)
        assert len(spool.queue) == 0, "spool did not finish"
        return 0

if __name__ == "__main__":
    main()
