# fusepy File System

This is a simple user-level file system, implemented using ```fusepy``` (a Python module that provides a simple interface to FUSE and MacFUSE). Note that because of its simplicity, it does not yet support a multi-level directory structure.

## Instructions

### Setup

File systems require some form of disk storage to persist files. For this file system, we create and initialize data structures on a file, which will emulate a block-addressable disk device. Open terminal in the root directory, and execute the following instructions.

```bash
# Creating the disk device.
> python3 disktools.py

# Initializing data structures on the disk device.
> python3 format.py
```

Thereafter, we will create a folder called ```mount``` in the root directory, where we will later mount our file system.

```bash
mkdir mount
```

### Running the file system

1. Launch two terminals in the root directory.
2. Mount the file system into the newly created folder, using the first terminal.

```bash
> python3 small.py mount
```

3. Use the mounted file system in the second terminal, by switching directories.

```bash
> cd mount
```
