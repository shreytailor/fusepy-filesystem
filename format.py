# This is a formatting utility for the SMALL file system.
# Written By: Shrey Tailor

# Importing the necessary things.
import os
from time import time
from disktools import *

# Defining some important constants.
MASTER_BLOCKS = 5
TOTAL_BLOCKS = 16

# Getting and writing the metadata for the root directory.
now = time()
name_bytearray = bytearray(16)

files = int_to_bytes(0, 1)
fd = int_to_bytes(0, 1)
st_size = int_to_bytes(0, 2)
st_ctime = int_to_bytes(int(now), 4)
st_atime = int_to_bytes(int(now), 4)
st_mtime = int_to_bytes(int(now), 4)
st_nlink = int_to_bytes(2, 1)
st_mode = int_to_bytes(16877, 2)
st_uid = int_to_bytes(os.getuid(), 2)
st_gid = int_to_bytes(os.getgid(), 2)

root_bytearray = files + fd + st_size + st_ctime + st_atime + st_mtime + st_nlink + st_mode + st_uid + st_gid
write_block(0, root_bytearray)


# Go through all the regular blocks, and initializing them as not being used.
for block_number in range(MASTER_BLOCKS, TOTAL_BLOCKS):

    # Writing '1' to the first byte of each block to signal the unoccupied state.
    write_block(block_number, int_to_bytes(1, 1))