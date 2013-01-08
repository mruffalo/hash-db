#!/usr/bin/env python
from argparse import ArgumentParser
from os import walk
from os.path import isfile, join as ospj, normpath, relpath
from subprocess import Popen, PIPE

HASH_COMMAND = 'sha512sum'
HASH_FILENAME = b'SHA512SUM'

ADDED_COLOR = '\033[01;32m'
REMOVED_COLOR = '\033[01;34m'
MODIFIED_COLOR = '\033[01;31m'
NO_COLOR = '\033[00m'

def read_hash_output(line):
    pieces = line.strip().split(b'  ', 1)
    return normpath(pieces[1]), pieces[0]

def read_saved_hashes(hash_file):
    hashes = {}
    with open(hash_file, 'rb') as f:
        for line in f:
            filename, file_hash = read_hash_output(line)
            hashes[filename] = file_hash
    return hashes

def get_hashes(directory):
    hashes = {}
    for dirpath, _, filenames in walk(directory):
        for filename in filenames:
            if filename != HASH_FILENAME:
                command = [HASH_COMMAND, ospj(dirpath, filename)]
                output = Popen(command, stdout=PIPE).communicate()[0]
                filename, file_hash = read_hash_output(output)
                hashes[relpath(filename, directory)] = file_hash
    return hashes

def hash_diff(real: dict, saved: dict):
    """
    real and saved are dicts that map filenames to SHA512 hash values
    """
    added = real.keys() - saved.keys()
    removed = saved.keys() - real.keys()
    modified = set()
    for filename in real.keys() & saved.keys():
        if real[filename] != saved[filename]:
            modified.add(filename)
    return added, removed, modified

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('directory', nargs='*', default=[b'.'],
                        type=lambda s: s.encode())
    args = parser.parse_args()
    for path in args.directory:
        sha512sum_file = ospj(path, HASH_FILENAME)
        if not isfile(sha512sum_file):
            raise EnvironmentError("Can't examine hashes in {}; no {} file".format(
                path, HASH_FILENAME))
        print('Reading hashes from {} ...'.format(sha512sum_file))
        saved = read_saved_hashes(sha512sum_file)
        print('done.')
        print('Hashing files in {} ...'.format(path))
        real = get_hashes(path)
        print('done.')
        print()
        added, removed, modified = hash_diff(real, saved)
        if added:
            print(ADDED_COLOR + 'Added files:' + NO_COLOR)
            for filename in sorted(added):
                print(filename)
            print()
        if removed:
            print(REMOVED_COLOR + 'Removed files:' + NO_COLOR)
            for filename in sorted(removed):
                print(filename)
            print()
        if modified:
            print(MODIFIED_COLOR + 'Modified files:' + NO_COLOR)
            for filename in sorted(modified):
                print(filename)
            print()
