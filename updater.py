import sys
import time
import requests
import os
import shutil

def main():
    if len(sys.argv) < 3:
        return

    url = sys.argv[1]
    target = sys.argv[2]

    time.sleep(1)

    r = requests.get(url)
    open("new.exe", "wb").write(r.content)

    try:
        os.remove(target)
    except:
        time.sleep(1)
        os.remove(target)

    shutil.move("new.exe", target)

    os.startfile(target)

if __name__ == "__main__":
    main()
