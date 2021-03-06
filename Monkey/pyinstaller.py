#! /usr/bin/env python
# -----------------------------------------------------------------------------
# Copyright (c) 2013, PyInstaller Development Team.
#
# Distributed under the terms of the GNU General Public License with exception
# for distributing bootloader.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------
"""
Main command-line interface to PyInstaller.
"""

if __name__ == '__main__':
    from PyInstaller.__main__ import run

    # opts=['DlgHello.py','-F','-
    #opts = ['autoTool15.py', '-F','-c']
    opts = ['monkeytest.py', '-F', '-c']
    #opts = ['helloWorld.py', '-F']
    run(opts)