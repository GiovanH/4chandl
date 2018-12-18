#!/bin/python3
from distutils.dir_util import copy_tree
from glob import glob
from os.path import sep, getmtime
from send2trash import send2trash
from time import sleep
from traceback import print_exc
import _thread as thread


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
    srcdir = input("Read folders in what directory? (glob) ")
    inter = srcdir.replace("/", sep) + "{s}*{s}".format(s=sep)
    globbed = glob(inter)
    globbed = sorted(globbed, key=getmtime)
    for path in globbed:
        print(path)
        ans = input("?> ")
        try:
            if ans == "":
                continue
            try:
                start_thread(ans, renameDir, (path, ans, ))
                # renameDir(path, ans)
                sleep(0.1)
            except Exception as e:
                print("Error: unable to start thread")
                raise
        except ValueError:
            print("Invalid input. ")  # Have another go.


threads = []


def start_thread(name, f, args):
    def closure(f, args, name):
        threads.append(name)
        f(*args)
        threads.remove(name)

    thread.start_new_thread(closure, (f, args, name, ))


def run_threaded():
    try:
        main()
    except (Exception, KeyboardInterrupt) as e:
        # Postmortem on uncaught exceptions
        print_exc()

    # Cleanup
    while (len(threads) > 0):
        print("Waiting for jobs to finish:")
        print("\n".join(["- {}".format(t) for t in threads]))
        sleep(0.8)
    print("Finished.")


if __name__ == "__main__":
    run_threaded()
