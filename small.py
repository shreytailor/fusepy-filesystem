#!/usr/bin/env python

# This is the implementation for our SMALL file system.
# Written by: Shrey Tailor

from __future__ import print_function, absolute_import, division

import os
import logging
from time import time
from disktools import *
from errno import ENOENT
from collections import defaultdict
from stat import S_IFDIR, S_IFLNK, S_IFREG
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

# Defining some important constants.
MASTER_BLOCKS = 5
TOTAL_BLOCKS = 16

class Small(LoggingMixIn, Operations):

    def chmod(self, path, mode):
        self.files[path]['st_mode'] &= 0o770000
        self.files[path]['st_mode'] |= mode
        return 0


    def chown(self, path, uid, gid):
        self.files[path]['st_uid'] = uid
        self.files[path]['st_gid'] = gid


    def create(self, path, mode):
        # Get the total amount of files currently existing.
        first_master_block = read_block(0)
        num_of_files = bytes_to_int(first_master_block[0:1])
        
        if (num_of_files == 4):
            raise IOError("This file system can only capacitate four files at any given time.")

        # Find first empty block from the regular blocks.
        free_block = 0
        for block in range(MASTER_BLOCKS, TOTAL_BLOCKS):
            block_bytes = read_block(block)
            is_free = bytes_to_int(block_bytes[0:1])

            if (is_free == 1):
                free_block = block
                block_bytes[0:1] = int_to_bytes(0, 1)
                write_block(block, block_bytes)
                break

        if (free_block == 0):
            raise IOError("There is no space remaining in the current disk.")
        
        # Creating the bytearray containing the file attributes.
        now = time()
        name_block = bytearray(16)
        name_block[0:16] =  path[1:].encode()
        block_location = int_to_bytes(free_block, 1)
        st_size = int_to_bytes(0, 2)
        st_ctime = int_to_bytes(int(now), 4)
        st_atime = int_to_bytes(int(now), 4)
        st_mtime = int_to_bytes(int(now), 4)
        st_nlink = int_to_bytes(1, 1)
        st_mode = int_to_bytes(S_IFREG | mode, 2)
        st_uid = int_to_bytes(os.getuid(), 2)
        st_gid = int_to_bytes(os.getgid(), 2)
        bytearray_segment = st_mode + st_nlink + st_size + st_ctime + st_atime + st_mtime + st_uid + st_gid

        # Inserting the data structure to the allocated master block.
        master_entry = read_block(num_of_files + 1)
        master_entry[0:1] = block_location
        master_entry[1:17] = name_block
        master_entry[17:34] = bytearray_segment
        write_block(num_of_files + 1, master_entry)

        # Increment the number of files.
        num_of_files = num_of_files + 1
        fd = bytes_to_int(first_master_block[1:2]) + 1
        first_master_block[0:1] = int_to_bytes(num_of_files, 1)
        first_master_block[1:2] = int_to_bytes(fd, 1)
        write_block(0, first_master_block)
        return fd


    def getattr(self, path, fh=None):
        if (path == '/'):
            attr_bytearray = read_block(0)
            attr_dict = dict(
                st_mode=bytes_to_int(attr_bytearray[17:19]),
                st_nlink=bytes_to_int(attr_bytearray[16:17]),
                st_size=bytes_to_int(attr_bytearray[2:4]),
                st_ctime=bytes_to_int(attr_bytearray[4:8]),
                st_mtime=bytes_to_int(attr_bytearray[12:16]),
                st_atime=bytes_to_int(attr_bytearray[8:12]),
                st_uid=bytes_to_int(attr_bytearray[19:21]),
                st_gid=bytes_to_int(attr_bytearray[21:23]))
            return attr_dict
        else:

            # Accessing data for each file in master segment, and checking the matching filename.
            for counter in range(1, MASTER_BLOCKS):

                # Get the file atttributes, and checking the string if it matches.
                file_attrs = read_block(counter)
                if (str(file_attrs[1:17].decode().encode())[1:].replace('\\x00', "") == str(path[1:].encode())[1:]):
                    attr_dict = dict(
                        st_mode=bytes_to_int(file_attrs[17:19]),
                        st_nlink=bytes_to_int(file_attrs[19:20]),
                        st_size=bytes_to_int(file_attrs[20:22]),
                        st_ctime=bytes_to_int(file_attrs[22:26]),
                        st_mtime=bytes_to_int(file_attrs[30:34]),
                        st_atime=bytes_to_int(file_attrs[26:30]),
                        st_uid=bytes_to_int(file_attrs[34:36]),
                        st_gid=bytes_to_int(file_attrs[36:38]))
                    return attr_dict

            raise FuseOSError(ENOENT)


    # This method has been modified by removing the existing code, and replacing it with a stub.
    def getxattr(self, path, name, position=0):
        return bytes()


    # This method has been modified by removing the existing code, and replacing it with a stub.
    def listxattr(self, path):
        return bytes()


    def open(self, path, flags):
        root_record = read_block(0)
        fd = bytes_to_int(root_record[1:2])
        fd = fd + 1
        root_record[1:2] = int_to_bytes(fd, 1)
        write_block(0, root_record)
        return fd


    def read(self, path, size, offset, fh):

        # Accessing data for each file and checking the filename if it matches.
        for counter in range(1, MASTER_BLOCKS):

            # Get the file atttributes, and checking the string if it matches.
            file_attrs = read_block(counter)
            if (str(file_attrs[1:17].decode().encode())[1:].replace('\\x00', "") == str(path[1:].encode())[1:]):

                # Finding the block containing the file data, and reading the data.
                data_block = bytes_to_int(file_attrs[0:1])
                overall_string = bytearray()

                # While there is a next block, keep reading the text and appending it to the end.
                while (data_block != 0):
                    d_contents = read_block(data_block)
                    overall_string = overall_string + d_contents[2:64]

                    block_contents = read_block(data_block)
                    data_block = bytes_to_int(block_contents[1:2])

                # Return the final string after everything was collected.
                return str.encode(overall_string.decode().replace('\x00', ''))


    def readdir(self, path, fh):

        # Array that contains the files in the file system.
        file_array = []
        for counter in range(1, MASTER_BLOCKS):
            # Get the data_block attribute, and file exists is that attribute is zero.
            file_attrs = read_block(counter)

            if (bytes_to_int(file_attrs[0:1]) != 0):
                file_name = file_attrs[1:17].decode().replace('\x00', '')
                file_array.append(file_name)

        # Return the array of all files in the file system.
        return ['.', '..'] + file_array


    def readlink(self, path):
        return self.data[path]


    # This method has been modified by removing the existing code, and replacing it with a stub.
    def removexattr(self, path, name):
        return bytes()


    # This method has been modified by removing the existing code, and replacing it with a stub.
    def setxattr(self, path, name, value, options, position=0):
        return bytes()


    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)


    def truncate(self, path, length, fh=None):

        # Truncating the file so that it's exactly 'length' bytes long. This call is required for
        # read/write file systems, because recreating the file will firstly truncate it. In our,
        # file system, it would be required to recreate the files in the following calls.

        # echo "shrey" > myname
        # echo "tailor" > myname

        # Hence, we use the previously written functions to carry out the functionality.
        self.unlink(path)
        self.create(path, 33188)


    def unlink(self, path):

        # Finding the master block belonging to the file we are looking for.
        # Accessing data for each file and checking the filename if it matches.
        for counter in range(1, MASTER_BLOCKS):

            # Get the file atttributes, and checking the string if it matches.
            file_attrs = read_block(counter)
            if (str(file_attrs[1:17].decode().encode())[1:].replace('\\x00', "") == str(path[1:].encode())[1:]):

                # Getting the data block for this file.
                data_block = bytes_to_int(file_attrs[0:1])
                data_block_content = read_block(data_block)

                # Tracking the blocks which belong to this file.
                block_array = []
                block_array.append(data_block)
                while bytes_to_int(data_block_content[1:2]) != 0:
                    data_block = bytes_to_int(data_block_content[1:2])
                    data_block_content = read_block(data_block)
                    block_array.append(data_block)
                
                # Emptying blocks which belong to the file.
                default_data_block = bytearray(64)
                default_data_block[0:1] = int_to_bytes(1, 1)
                for block in block_array:
                    write_block(block, default_data_block)
            
                # Emptying current master block and then moving all master blocks.
                default_master_block = bytearray(64)
                for x in range(counter, MASTER_BLOCKS):
                    write_block(x, default_master_block)
                    write_block(x, read_block(x + 1))
                write_block(MASTER_BLOCKS - 1, default_master_block)

                # Decreaasing the amount of files there are in the file system.
                root_block = read_block(0)
                num_of_files = bytes_to_int(root_block[0:1])
                root_block[0:1] = int_to_bytes(num_of_files - 1, 1)
                write_block(0, root_block)


    def utimens(self, path, times=None):
        now = time()
        atime, mtime = times if times else (now, now)

        # Accessing data for each file and checking the filename if it matches.
        for counter in range(1, MASTER_BLOCKS):

            # Get the file atttributes, and checking the string if it matches.
            file_attrs = read_block(counter)
            if (str(file_attrs[1:17].decode().encode())[1:].replace('\\x00', "") == str(path[1:].encode())[1:]):
                file_attrs[30:34] = int_to_bytes(int(mtime), 4)
                file_attrs[26:30] = int_to_bytes(int(atime), 4)
                break;

            # Writing the updated block to the master segment.
            write_block(counter, file_attrs)


    def write(self, path, data, offset, fh):

        # Accessing data for each file and checking the filename if it matches.
        for counter in range(1, MASTER_BLOCKS):

            # Get the file atttributes, and checking the string if it matches.
            file_attrs = read_block(counter)

            # Updating the modified time of the file.
            now = time()
            file_attrs[30:34] = int_to_bytes(int(now), 4)

            if (str(file_attrs[1:17].decode().encode())[1:].replace('\\x00', "") == str(path[1:].encode())[1:]):

                # If the file doesn't yet contain any data (i.e. echo "Shrey" > filename)
                if (offset == 0):
                    num_of_bytes = len(data)
                    blocks_required = int(num_of_bytes / 62)

                    # Find required free blocks, and add to the list below.
                    free_blocks = []
                    for block in range(MASTER_BLOCKS, TOTAL_BLOCKS):
                        block_bytes = read_block(block)
                        is_free = bytes_to_int(block_bytes[0:1])

                        if (is_free == 1):
                            free_blocks.append(block)
                            block_bytes[0:1] = int_to_bytes(0, 1)
                            write_block(block, block_bytes)
                        
                        if (len(free_blocks) == blocks_required):
                            break;

                    # Check if we have enough blocks to hold the data.
                    if (len(free_blocks) != blocks_required):
                        self.unlink(path)
                        raise FuseOSError("There is no space remaining in the current disk.")

                    # Start the process of adding the data to the blocks.
                    block_no = bytes_to_int(file_attrs[0:1])
                    b_contents = read_block(block_no)

                    if (len(free_blocks) > 0):
                        b_contents[1:2] = int_to_bytes(free_blocks[0], 1)
                    
                    b_contents[2:64] = data[0:62]
                    write_block(block_no, b_contents)

                    for block in range(0, len(free_blocks)):
                        b_contents = read_block(free_blocks[block])
                        
                        if (block < len(free_blocks) - 1):
                            b_contents[1:2] = int_to_bytes(free_blocks[block + 1], 1)
                        
                        starting_limit = 62 * (block + 1)
                        ending_limit = min(62 * (block + 2), len(data))

                        b_contents[0:1] = int_to_bytes(0, 1)
                        b_contents[2:64] = data[starting_limit:ending_limit]
                        write_block(free_blocks[block], b_contents)
                    
                    # Returning the length of the data, and writing the size metadata.
                    file_attrs[20:22] = int_to_bytes(len(data), 2)
                    write_block(counter, file_attrs)
                else:

                    # Getting basic file attributes before running the algorithm.
                    current_size = bytes_to_int(file_attrs[20:22])
                    blocks_currently_occupied = int(current_size / 62) + 1
                    current_block_vacant_space = (blocks_currently_occupied * 62) - current_size

                    # Go to the last block.
                    current_block_no = bytes_to_int(file_attrs[0:1])
                    for y in range(0, blocks_currently_occupied - 1):
                        current_block_data = read_block(current_block_no)
                        current_block_no = bytes_to_int(current_block_data[1:2])
                    
                    # Different process depending on if new data can fit in assigned blocks.
                    if (len(data) <= current_block_vacant_space):

                        # Read in data from the last block, get its data, append and write it.
                        current_block_data = read_block(current_block_no)
                        limit = (current_size + 62) % 62 
                        current_block_data[2 + limit + 1:2 + (limit + 1) + len(data)] = data
                        write_block(current_block_no, current_block_data)

                        # Updating the current size of the file.
                        current_size = current_size + len(data)
                        file_attrs[20:22] = int_to_bytes(current_size, 2)
                        write_block(counter, file_attrs)

                    else:

                        # Finding out how many more blocks would be required to store the new data.
                        num_blocks_req = int((len(data) - current_block_vacant_space) / 62) + 1

                        # Find required free blocks, and add to the list below.
                        free_blocks = []
                        for block in range(MASTER_BLOCKS, TOTAL_BLOCKS):
                            block_bytes = read_block(block)
                            is_free = bytes_to_int(block_bytes[0:1])

                            if (is_free == 1):
                                free_blocks.append(block)
                            if (len(free_blocks) == num_blocks_req):
                                break;

                        # Check if we have enough blocks to hold the data.
                        if (len(free_blocks) != num_blocks_req):
                            raise FuseOSError("There is no space remaining in the current disk.")
                        
                        # Complete the current block before starting the new.
                        data_index = 0;
                        current_block_data = read_block(current_block_no)
                        current_block_vacant_space = current_block_vacant_space - 1
                        for y in range(0, current_block_vacant_space):
                            current_block_data[2 + (62 - current_block_vacant_space) + y] = data[y]
                            data_index = data_index + 1

                        # Writing current block back to the disk.
                        current_block_data[1:2] = int_to_bytes(free_blocks[0], 1)
                        write_block(current_block_no, current_block_data)

                        # Starting to write in the new blocks.
                        for y in range(0, len(free_blocks)):
                            b_contents = read_block(free_blocks[y])

                            if (y < len(free_blocks) - 1):
                                b_contents[1:2] = int_to_bytes(free_blocks[y + 1], 1)
                            else:
                                b_contents[1:2] = int_to_bytes(0, 1)    

                            starting_limit = data_index
                            ending_limit = data_index + min(data_index + 62, len(data) - 1)
                            
                            b_contents[0:1] = int_to_bytes(0, 1)
                            b_contents[2:64] = data[starting_limit:ending_limit]

                            data_index = data_index + 62
                            write_block(free_blocks[y], b_contents)

                        # Returning the length of the data, and writing the size metadata.
                        new_size = len(data) + bytes_to_int(file_attrs[20:22])
                        file_attrs[20:22] = int_to_bytes(new_size, 2)
                        write_block(counter, file_attrs)
        
        return len(data)


# --------------------------------------------------------------------------------------
# --- MAIN FUNCTION ---
# --------------------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('mount')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    fuse = FUSE(Small(), args.mount, foreground=True)