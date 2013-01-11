#!/usr/bin/env python3
from argparse import ArgumentParser
import hashlib
import json
from mmap import mmap, ACCESS_READ
from os import stat, walk
from os.path import abspath, dirname, isfile, join as ospj, normpath, relpath
from sys import stdout

HASH_FILENAME = 'SHA512SUM'
DB_FILENAME = 'hash_db.json'
HASH_FUNCTION = hashlib.sha512
# Mostly used for importing from saved hash files
EMPTY_FILE_HASH = ('cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce'
                   '47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e')

ADDED_COLOR = '\033[01;32m'
REMOVED_COLOR = '\033[01;34m'
MODIFIED_COLOR = '\033[01;31m'
NO_COLOR = '\033[00m'

# Not used yet. For future expansion.
DATABASE_VERSION = 1

def read_hash_output(line):
    pieces = line.strip().split('  ', 1)
    return normpath(pieces[1]), pieces[0]

def read_saved_hashes(hash_file, encoding):
    hashes = {}
    with open(hash_file, encoding=encoding) as f:
        i = -1
        try:
            for i, line in enumerate(f):
                filename, file_hash = read_hash_output(line)
                hashes[filename] = file_hash
        except UnicodeDecodeError as e:
            print('in {} line {}'.format(hash_file, i + 1))
            raise
    return hashes

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
        raise FileNotFoundError(message.format(HASH_FILENAME, path))
    return filename

class HashEntry:
    def __init__(self, filename, size=None, mtime=None, hash=None):
        # In memory, "filename" should be an absolute path
        self.filename = filename
        self.size = size
        self.mtime = mtime
        self.hash = hash

    def hash_file(self):
        if stat(self.filename).st_size > 0:
            with open(self.filename, 'rb') as f:
                with mmap(f.fileno(), 0, access=ACCESS_READ) as m:
                    return HASH_FUNCTION(m).hexdigest()
        else:
            return EMPTY_FILE_HASH

    def exists(self):
        return isfile(self.filename)

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
        try:
            self.path = dirname(find_hash_db(path))
        except FileNotFoundError:
            self.path = path
        self.entries = {}

    def save(self):
        filename = ospj(self.path, DB_FILENAME)
        data = {
            'version': DATABASE_VERSION,
            'files': {
                relpath(entry.filename, self.path): {
                    'size': entry.size,
                    'mtime': entry.mtime,
                    'hash': entry.hash,
                }
                for entry in self.entries.values()
            }
        }
        with open(filename, 'w') as f:
            json.dump(data, f)

    def load(self):
        filename = find_hash_db(self.path)
        with open(filename) as f:
            data = json.load(f)
        for filename, entry_data in data['files'].items():
            entry = HashEntry(abspath(ospj(self.path, filename)))
            entry.size = entry_data['size']
            entry.mtime = entry_data['mtime']
            entry.hash = entry_data['hash']
            self.entries[entry.filename] = entry

    def import_hashes(self, filename, encoding):
        """
        Imports a hash file created by e.g. sha512sum, and populates
        the database with this data. Examines each file to obtain the
        size and mtime information.
        """
        hashes = read_saved_hashes(filename, encoding)
        for filename, hash in hashes.items():
            entry = HashEntry(abspath(ospj(self.path, filename.replace('\\\\', '\\'))))
            entry.hash = hash
            entry.update_attrs()
            self.entries[entry.filename] = entry
        return len(self.entries)

    def update(self, rehash=False):
        """
        Walks the filesystem, adding and removing files from
        the database as appropriate.
        """
        added = set()
        modified = set()
        existing_files = set()
        for dirpath, _, filenames in walk(self.path):
            for filename in filenames:
                if filename == DB_FILENAME:
                    continue
                abs_filename = abspath(ospj(dirpath, filename))
                existing_files.add(abs_filename)
                if abs_filename in self.entries:
                    entry = self.entries[abs_filename]
                    st = stat(abs_filename)
                    if rehash or entry.size != st.st_size or entry.mtime != st.st_mtime:
                        modified.add(entry.filename)
                        entry.update()
                else:
                    entry = HashEntry(abs_filename)
                    entry.update()
                    self.entries[abs_filename] = entry
                    added.add(entry.filename)
        removed = self.entries.keys() - existing_files
        for deleted_file in removed:
            del self.entries[deleted_file]
        return added, removed, modified

    def verify(self):
        """
        Calls each HashEntry's verify method to make sure that
        nothing has changed on disk.

        Yields each filename with different contents than was
        recorded here.
        """
        modified = set()
        removed = set()
        count = len(self.entries)
        i = -1
        for i, (filename, entry) in enumerate(self.entries.items()):
            if entry.exists():
                if not entry.verify():
                    modified.add(entry.filename)
            else:
                removed.add(entry.filename)
            stdout.write('\rChecked {} of {} files'.format(i + 1, count))
        if i >= 0:
            print()
        return modified, removed

def print_file_lists(added, removed, modified):
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

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('command')
    parser.add_argument('directory', default='.')
    parser.add_argument('-n', '--pretend', action='store_true')
    parser.add_argument('--rehash', action='store_true', help=('Force the "update" '
        'command to rehash all files instead of omitting those with identical'
        'size and modification time.'))
    parser.add_argument('--import-encoding', default=None, help=('Encoding of the '
        'file used for import. Default: utf-8.'))
    args = parser.parse_args()
    db = HashDatabase(args.directory)
    if args.command == 'init':
        print('Initializing hash database')
        added, removed, modified = db.update()
        print_file_lists(added, removed, modified)
        if not args.pretend:
            db.save()
    elif args.command == 'update':
        print('Updating hash database')
        db.load()
        added, removed, modified = db.update(rehash=args.rehash)
        print_file_lists(added, removed, modified)
        if not args.pretend:
            db.save()
    elif args.command == 'import':
        print('Importing hash database')
        count = db.import_hashes(ospj(args.directory, HASH_FILENAME),
                                 encoding=args.import_encoding)
        print('Imported {} entries'.format(count))
        if not args.pretend:
            db.save()
    elif args.command == 'verify':
        db.load()
        modified, removed = db.verify()
        print_file_lists(None, removed, modified)
    else:
        print('Bad command: {}'.format(args.command))
