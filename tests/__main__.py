import os
import sys


def main():
    print '\n\nRunning Test Suite...\n\n'
    os.system('mayapy -m unittest discover tests')


if __name__ == '__main__':
    main()
