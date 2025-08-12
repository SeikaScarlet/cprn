# -*- coding : utf-8 -*-
# create date : Oct 17th, 24
# last update : Aug 12th, 25
# author : seika<seika@live.ca>

"""
topic : general pickle dump and load tools for lsf (moved from taisl_sop)
"""


import hashlib
import os
import pickle

from datetime import datetime


class PickleIO:
    """ Pickle IO
    """
    @staticmethod
    def pickle_dump(obj, file_path: str):
        """ pickle dump
        """
        with open(file_path, 'wb') as f:
            pickle.dump(obj, f)

    @staticmethod
    def pickle_load(file_path: str):
        """ pickle load
        """
        with open(file_path, 'rb') as f:
            return pickle.load(f)
        
    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """ get sha-256 hash of file
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()

        return checksum

    @staticmethod
    def rename_file(old_file_path: str, new_file_path: str):
        try:
            os.rename(old_file_path, new_file_path)
            print(f"File renamed from {old_file_path} to {new_file_path}")
        except Exception as e:
            print(f"Error renaming file: {e}")

    @staticmethod
    def dump_as_pickle(obj, file_path: str):
        """ dump as pickle file and rename with date and hash
        """
        PickleIO.pickle_dump(obj, file_path)

        sha256_hash = PickleIO.get_file_hash(file_path)
        date_str = datetime.now().strftime("%y%m%d")

        filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
        new_file_name = f"{filename_without_ext}_{date_str}_{sha256_hash}.pkl"
        new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
        
        PickleIO.rename_file(file_path, new_file_path)
    
    @staticmethod
    def load_from_pickle(file_path: str):
        """ load pickle from file and check hash (signature from filename)
        """
        sha256_hash_loadfile = PickleIO.get_file_hash(file_path)
        sha256_hash_signature = os.path.basename(file_path).split("_")[-1].split(".")[0]
        
        if sha256_hash_loadfile != sha256_hash_signature:
            raise ValueError("File hash does not match")
        else:
            print(f"File hash checking : {sha256_hash_loadfile} : passed ")
        
        return PickleIO.pickle_load(file_path)