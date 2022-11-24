# PyInstaller pack
import datetime
import os
import subprocess
import sys

from PyInstaller.__main__ import run

if __name__ == '__main__':
    TIME = datetime.datetime.now().strftime("%Y%m%d")
    SRC_ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

    sys.path.append(SRC_ROOT_PATH)
    res_bool, commit_id = subprocess.getstatusoutput('git rev-parse HEAD')
    if res_bool == 1:
        print('Unable to get commit id')
        sys.exit(0)
    opts = ['-F',
            '-i', os.path.join(SRC_ROOT_PATH, 'assets', 'icon.ico'),
            '--clean', '--name', u'pyMIDIParse' + commit_id[:4] + "_" + TIME,
            f'{SRC_ROOT_PATH}/playback.py']
    # '--noupx'
    run(opts)
