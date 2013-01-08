#!/usr/bin/env python
from argparse import ArgumentParser
import hashlib
import json
from mmap import mmap, ACCESS_READ
from os import stat, walk
from os.path import abspath, dirname, isfile, join as ospj, normpath, relpath
from subprocess import Popen, PIPE

HASH_COMMAND = 'sha512sum'
HASH_FILENAME = b'SHA512SUM'
DB_FILENAME = 'hash_db.json'
HASH_FUNCTION = hashlib.sha512

ADDED_COLOR = '\033[01;32m'
REMOVED_COLOR = '\033[01;34m'
MODIFIED_COLOR = '\033[01;31m'
NO_COLOR = '\033[00m'

class HashEntry:
    def __init__(self, filename, size=None, mtime=None, hash=None):
        # In memory, "filename" should be an absolute path
        self.filename = filename
        self.size = size
        self.mtime = mtime
        self.hash = hash

    def hash_file(self):
        with open(self.filename, 'rb') as f:
            with mmap(f.fileno(), 0, access=ACCESS_READ) as m:
                return HASH_FUNCTION(m)

    def verify(self):
        return self.hash_file() == self.hash

    def update(self):
        self.hash = self.hash_file()
        s = stat(self.filename)
        self.size, self.mtime = s.st_size, s.st_mtime

class HashDatabase:
    def __init__(self):
        pass

    def dump(self, filename):
        pass

    def load(self, filename):
        pass

def find_hash_db_r(path):
    """
    Searches the given path and all of its parent
    directories to find a filename matching DB_FILENAME
    """
    abs_path = abspath(path)
    cur_path = ospj(abs_path, DB_FILENAME)
    if isfile(cur_path):
        return cur_path
    parent = dirname(abs_path)
    if parent != abs_path:
        return find_hash_db_r(parent)

def find_hash_db(path):
    filename = find_hash_db_r(path)
    if filename is None:
        message = "Couldn't find '{}' in '{}' or any parent directories"
        raise FileNotFoundError(message.format(HASH_FILENAME.decode(), path))
    return filename

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
