This script manages a simple database of SHA512 file hashes.

Intro/Motivation
================

One can hash all files in a directory (and all subdirectories) quite easily
with a shell alias like the following:

    alias sha512sum-all='find . '\''!'\'' -name SHA512SUM -type f -exec sha512sum {} + >> SHA512SUM'

However, updating this SHA512SUM file is not particularly efficient if we'd
like to avoid rehashing every file in the directory tree. Writing a script to
add and remove entries is relatively easy, but it would also be nice to update
the hashes for files that have changed. Using a plain SHA512SUM file makes it
quite difficult to identify files that have been modified, so this script
stores additional file metadata and stores the hashes in JSON format.

Usage
=====

The basic invocation of the script is of the form
    hash_db.py [options] command [directory]
The directory defaults to '.' (current directory) but can be overridden.

Commands
--------

* init

  Creates a hash database in the specified directory. Walks the directory tree
  and adds all files to the database. After completion, prints the list of
  added files.
* update

  Reads the hash database into memory and walks the directory tree to find any
  noteworthy files. This includes files that are not included in the hash
  database, files that have been removed since the last update, and files with
  a size or modification time that don't match the recorded values. Entries in
  the database are added, updated or modified as appropriate, and the new
  database is written to disk.
  Also supports a "pretend" option ('-n' or '--pretend') that omits writing the
  new database to disk.
* status

  Reports added, modified, and removed files without performing any file
  hashing.

  Note that certain filesystems (vfat in particular) seem to report
  spurious mtime changes, and 'status' necessarily will report such files.
  'update --pretend' can be used to filter these false positives at the cost of
  hashing each modified file.
* verify

  Reads the hash database into memory and hashes each file on disk. Reports
  each hash mismatch or file removal.
* import

  Initializes a hash database from a SHA512SUM file. Walks the directory tree
  to read the size and modification time of each file, but uses the saved hash
  values instead of hashing each file on disk.

Requirements
============

Python 3.3. I may eventually make this script run on 3.2 but probably not any
time soon.

Open Issues
===========

* All filenames MUST be valid UTF-8. This is a limitation of the current
  database storage format; Python's JSON module does not allow serializing byte
  strings. I intend to replace the storage format at some point (possibly with
  a SQLite database), so I'll deal with this at that time. It's probably also a
  good idea to use the new os.{fsencode, fsdecode} methods added in Python 3.2.
* The import functionality is quite limited. Hashes are only read from one
  SHA512SUM file, but it would be much nicer to read all SHA512SUM and
  hash\_db files that are present. This would allow the easy and efficient
  creation of a "parent" hash database from those in subdirectories.
* During the "verify" step, it would be nice to pretty-print the number of
  bytes hashed instead of or in addition to the number of files.

Addendum: One may notice that the operation and design of this hash database
are strikingly similar to Git's index. This is not a coincidence.

<!---
# vim: set tw=79:
-->
