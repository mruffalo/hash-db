#!/usr/bin/env python
from argparse import ArgumentParser
import hashlib
import json
from mmap import mmap, ACCESS_READ
from os import stat, walk
from os.path import abspath, dirname, isfile, join as ospj, normpath, relpath

HASH_FILENAME = b'SHA512SUM'
DB_FILENAME = 'hash_db.json'
HASH_FUNCTION = hashlib.sha512

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

    def update_attrs(self):
        s = stat(self.filename)
        self.size, self.mtime = s.st_size, s.st_mtime

    def update(self):
        self.update_attrs()
        self.hash = self.hash_file()

class HashDatabase:
    def __init__(self, path):
        self.path = path
        self.entries = {}

    def dump(self, filename):
        pass

    def load(self, filename):
        pass

    def import_hashes(self, filename):
        """
        Imports a hash file created by e.g. sha512sum, and populates
        the database with this data. Examines each file to obtain the
        size and mtime information.
        """
        pass

    def update(self):
        """
        Walks the filesystem, adding and removing files from
        the database as appropriate.
        """
        existing_files = set()
        for dirpath, _, filenames in walk(self.path):
            for filename in filenames:
                abs_filename = abspath(filename)
                existing_files.add(abs_filename)
                if abs_filename in self.entries:
                    entry = self.entries[abs_filename]
                    st = stat(abs_filename)
                    if entry.size != st.st_size or entry.mtime != st.st_mtime:
                        entry.update()
                else:
                    entry = HashEntry(abs_filename)
                    entry.update()
                    self.entries[abs_filename] = entry
        for deleted_file in self.entries.keys() - existing_files:
            del self.entries[deleted_file]

    def verify(self):
        """
        Calls each HashEntry's verify method to make sure that
        nothing has changed on disk.

        Yields each filename with different contents than was
        recorded here.
        """
        for filename, entry in self.entries.items():
            if not entry.verify():
                yield filename

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
    parser.add_argument('command')
    parser.add_argument('directory', default=b'.', type=lambda s: s.encode())
    args = parser.parse_args()
    db_file = find_hash_db(args.directory)
    db = HashDatabase(dirname(db_file))
