This script manages a simple database of SHA512 file hashes.

== Intro/Motivation ==

One can hash all files in a directory (and all subdirectories) quite easily
with a shell alias like the following:

alias sha512sum-all='find . '\''!'\'' -name SHA512SUM -type f -exec sha512sum {} + >> SHA512SUM'

However, updating this SHA512SUM file is not particularly efficient if we'd
like to avoid rehashing every file in the directory tree. Writing a script to
add and remove entries is relatively easy, but it would also be nice to update
the hashes for files that have changed. Using a plain SHA512SUM file makes it
quite difficult to identify files that have been modified, so this script
stores additional file metadata and stores the hashes in JSON format.

== Usage ==

The basic invocation of the script is of the form
  hash_db.py [options] command [directory]
The directory defaults to '.' (current directory) but can be overridden.

Commands:
* init
  Creates a hash database in the specified directory. Walks the directory tree
  and adds all files to the database. After completion, prints the list of
  added files.
* update
  Reads the hash database into memory and walks the directory tree to find any
  noteworthy files. This inclues files that are not included in the hash
  database, files that have been removed since the last update, and files with
  a size or modification time that don't match the recorded values. Entries in
  the database are added, updated or modified as appropriate, and the new
  database is written to disk.
  Also supports a "pretend" option ('-n' or '--pretend') that omits writing the
  new database to disk.
* verify
  Reads the hash database into memory and hashes each file on disk. Reports
  each hash mismatch or file removal.
* import
  Initializes a hash database from a SHA512SUM file. Walks the directory tree
  to read the size and modifiation time of each file, but uses the saved hash
  values instead of hashing each file on disk.

== Requirements ==

Python 3.3. I may eventally make this script run on 3.2 but probably not any
time soon.

== Open Issues ==

* All filenames MUST be valid UTF-8. This is a limitation of the current
  database storage format; Python's JSON module does not allow serializing byte
  strings. I intend to replace the storage format at some point (possibly with
  a SQLite database), so I'll deal with this at that time.
* The script does not handle symlinks very well. At the moment, the contents of
  the link's target are hashed as if the link is a regular file. Broken
  symlinks raise a FileNotFoundError and cause the script to fail.
* The import functionality is quite limited. Hashes are only read from one
  SHA512SUM file, but it would be much nicer to read all SHA512SUM and
  hash_db files that are present. This would allow the easy and efficient
  creation of a "parent" hash database from those in subdirectories.

Addendum: One may notice that the operation and design of this hash database
are strikingly similar to Git's index. This is not a coincidence.

# vim: set tw=79:
