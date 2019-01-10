#!/bin/python3
from distutils.dir_util import copy_tree
from glob import glob
from os.path import sep, getmtime
from send2trash import send2trash
from time import sleep
from traceback import print_exc
import loom


def renameDir(src, newName):
    dst = "{path}{s}{newName}{s}".format(path=sep.join(src.split(sep)[:-2]), newName=newName, s=sep)
    jobstr = "{} -> {}".format(src, dst)
    if dst.lower() == src.lower():
        print("Same.")
        return
    try:
        print(jobstr)
        copy_tree(src, dst)
        send2trash(src)
        return
    except Exception as e:
        print(e)
        raise


def main():
    srcdir = "saved/*"  # input("Read folders in what directory? (glob) ")
    inter = srcdir.replace("/", sep) + "{s}*{s}".format(s=sep)
    print(inter)
    globbed = glob(inter)
    globbed = sorted(globbed, key=getmtime)
    print(globbed)
    for path in globbed:
        print(path)
        ans = input("?> ")
        try:
            if ans == "":
                continue
            try:
                loom.thread(name=ans, target=renameDir, args=(path, ans, ))
                # renameDir(path, ans)
                sleep(0.1)
            except Exception as e:
                print("Error: unable to start thread")
                raise
        except ValueError:
            print("Invalid input. ")  # Have another go.

# threading.Thread(name=ans, target=renameDir, args=(path, ans, )).start()
def run_threaded():
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        # Postmortem on uncaught exceptions
        print_exc()

    # Cleanup
    loom.threadWait(1, 0.8)
    print("Finished.")


if __name__ == "__main__":
    run_threaded()
