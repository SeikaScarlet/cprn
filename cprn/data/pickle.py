# -*- coding : utf-8 -*-
# create date : Oct17'24
# last update : Sept24'25
# author : seika<seika@live.ca>

"""
topic : general pickle dump and load tools for lsf files (moved from taisl_sop)
further development will be conducted in this package
"""


import hashlib
import os
import pickle

import tarfile
import tempfile
import shutil

from datetime import datetime


class PickleIO:
    """ Pickle IO
    """
    @staticmethod
    def _pickle_dump(obj, file_path: str):
        """ pickle dump
        """
        with open(file_path, 'wb') as f:
            pickle.dump(obj, f)

    @staticmethod
    def _pickle_load(file_path: str):
        """ pickle load
        """
        with open(file_path, 'rb') as f:
            return pickle.load(f)
        
    @staticmethod
    def _get_file_hash(file_path: str) -> str:
        """ get sha-256 hash of file
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()

        return checksum

    @staticmethod
    def _rename_file(old_file_path: str, new_file_path: str):
        try:
            os.rename(old_file_path, new_file_path)
            print(f"File renamed from {old_file_path} to {new_file_path}")
        except Exception as e:
            print(f"Error renaming file: {e}")

    @staticmethod
    def _extract_hash_from_filename(file_path: str, file_extension: str = ".pkl") -> str:
        """ 从文件名中提取hash值
        
        Args:
            file_path: 文件路径
            file_extension: 文件扩展名 (.pkl 或 .tar.gz)
        
        Returns:
            str: 从文件名中提取的hash值
        """
        filename = os.path.basename(file_path)
        if file_extension == ".tar.gz":
            # 对于 .tar.gz 文件，hash在最后一个下划线和.tar.gz之间
            hash_part = filename.split("_")[-1].split(".tar.gz")[0]
        else:
            # 对于 .pkl 文件，hash在最后一个下划线和.pkl之间
            hash_part = filename.split("_")[-1].split(".")[0]
        
        return hash_part

    @staticmethod
    def _verify_file_hash(file_path: str, file_extension: str = ".pkl") -> bool:
        """ 验证文件hash是否与文件名中的hash匹配
        
        Args:
            file_path: 文件路径
            file_extension: 文件扩展名 (.pkl 或 .tar.gz)
        
        Returns:
            bool: True if hash matches, False otherwise
        """
        try:
            actual_hash = PickleIO._get_file_hash(file_path)
            filename_hash = PickleIO._extract_hash_from_filename(file_path, file_extension)
            
            if actual_hash != filename_hash:
                print(f"Hash mismatch! Actual: {actual_hash}, Filename: {filename_hash}")
                return False
            else:
                print(f"File hash checking : {actual_hash} : passed")
                return True
        except Exception as e:
            print(f"Error verifying hash: {e}")
            return False

    @staticmethod
    def _generate_filename_with_hash(base_file_path: str, file_extension: str = ".pkl") -> str:
        """ 生成带hash的文件名
        
        Args:
            base_file_path: 基础文件路径
            file_extension: 文件扩展名 (.pkl 或 .tar.gz)
        
        Returns:
            str: 带hash的完整文件路径
        """
        filename_without_ext = os.path.splitext(os.path.basename(base_file_path))[0]
        date_str = datetime.now().strftime("%y%m%d")
        
        # 先创建临时文件来计算hash
        temp_file = tempfile.NamedTemporaryFile(suffix=file_extension, delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # 复制文件到临时位置计算hash
            shutil.copy2(base_file_path, temp_path)
            sha256_hash = PickleIO._get_file_hash(temp_path)
            
            # 生成最终文件名
            new_file_name = f"{filename_without_ext}_{date_str}_{sha256_hash}{file_extension}"
            new_file_path = os.path.join(os.path.dirname(base_file_path), new_file_name)
            
            return new_file_path
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def dump_as_pickle(obj, file_path: str, compress: bool = False):
        """ dump as pickle file and rename with date and hash
        
        Args:
            obj: object to pickle
            file_path: target file path
            compress: if True, compress the pickle file using tar.gz
        """
        if compress:
            PickleIO._dump_as_pickle_compressed(obj, file_path)
        else:
            PickleIO._dump_as_pickle_uncompressed(obj, file_path)
    
    @staticmethod
    def _dump_as_pickle_uncompressed(obj, file_path: str):
        """ dump as uncompressed pickle file and rename with date and hash
        """
        PickleIO._pickle_dump(obj, file_path)

        sha256_hash = PickleIO._get_file_hash(file_path)
        date_str = datetime.now().strftime("%y%m%d")

        filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
        new_file_name = f"{filename_without_ext}_{date_str}_{sha256_hash}.pkl"
        new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
        
        PickleIO._rename_file(file_path, new_file_path)
    
    @staticmethod
    def _dump_as_pickle_compressed(obj, file_path: str):
        """ dump as compressed pickle file using tar.gz and rename with date and hash
        """
        # 创建临时文件
        temp_pkl_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        temp_pkl_path = temp_pkl_file.name
        temp_pkl_file.close()
        
        try:
            # 先保存为临时pickle文件
            PickleIO._pickle_dump(obj, temp_pkl_path)
            
            # 生成压缩文件名（先用临时hash）
            filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
            date_str = datetime.now().strftime("%y%m%d")
            temp_compressed_name = f"{filename_without_ext}_{date_str}_temp.tar.gz"
            temp_compressed_path = os.path.join(os.path.dirname(file_path), temp_compressed_name)
            
            # 创建tar.gz压缩文件
            with tarfile.open(temp_compressed_path, 'w:gz') as tar:
                tar.add(temp_pkl_path, arcname=f"{filename_without_ext}.pkl")
            
            # 计算压缩文件的hash
            sha256_hash = PickleIO._get_file_hash(temp_compressed_path)
            
            # 重命名为最终文件名
            final_file_name = f"{filename_without_ext}_{date_str}_{sha256_hash}.tar.gz"
            final_file_path = os.path.join(os.path.dirname(file_path), final_file_name)
            
            PickleIO._rename_file(temp_compressed_path, final_file_path)
            print(f"Compressed pickle file saved as: {final_file_path}")
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_pkl_path):
                os.unlink(temp_pkl_path)
    
    @staticmethod
    def load_from_pickle(file_path: str, compress: bool = False):
        """ load pickle from file and check hash (signature from filename)
        
        Args:
            file_path: pickle file path
            compressed: if True, load from compressed tar.gz file
        """
        if compress:
            return PickleIO._load_from_pickle_compressed(file_path)
        else:
            return PickleIO._load_from_pickle_uncompressed(file_path)
    
    @staticmethod
    def _load_from_pickle_uncompressed(file_path: str):
        """ load uncompressed pickle from file and check hash
        """
        if not PickleIO._verify_file_hash(file_path, ".pkl"):
            raise ValueError("File hash does not match")
        
        return PickleIO._pickle_load(file_path)
    
    @staticmethod
    def _load_from_pickle_compressed(file_path: str):
        """ load compressed pickle from tar.gz file and check hash
        """
        # 验证压缩文件的hash
        if not PickleIO._verify_file_hash(file_path, ".tar.gz"):
            raise ValueError("File hash does not match")
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 解压tar.gz文件
            with tarfile.open(file_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            # 找到解压出的pkl文件
            pkl_files = [f for f in os.listdir(temp_dir) if f.endswith('.pkl')]
            if not pkl_files:
                raise ValueError("No pickle file found in compressed archive")
            
            pkl_file_path = os.path.join(temp_dir, pkl_files[0])
            
            # 加载pickle文件
            return PickleIO._pickle_load(pkl_file_path)
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)


### ------ 

### class PickleIO:
###     """ Pickle IO
###     """
###     @staticmethod
###     def _pickle_dump(obj, file_path: str):
###         """ pickle dump
###         """
###         with open(file_path, 'wb') as f:
###             pickle.dump(obj, f)
### 
###     @staticmethod
###     def _pickle_load(file_path: str):
###         """ pickle load
###         """
###         with open(file_path, 'rb') as f:
###             return pickle.load(f)
###         
###     @staticmethod
###     def _get_file_hash(file_path: str) -> str:
###         """ get sha-256 hash of file
###         """
###         sha256_hash = hashlib.sha256()
###         with open(file_path, 'rb') as f:
###             for byte_block in iter(lambda: f.read(4096), b""):
###                 sha256_hash.update(byte_block)
###         checksum = sha256_hash.hexdigest()
###         return checksum
### 
###     @staticmethod
###     def _rename_file(old_file_path: str, new_file_path: str):
###         try:
###             os.rename(old_file_path, new_file_path)
###             print(f"File renamed from {old_file_path} to {new_file_path}")
###         except Exception as e:
###             print(f"Error renaming file: {e}")
### 
###     @staticmethod
###     def dump_as_pickle(obj, file_path: str):
###         """ dump as pickle file and rename with date and hash
###         """
###         PickleIO._pickle_dump(obj, file_path)
### 
###         sha256_hash = PickleIO._get_file_hash(file_path)
###         date_str = datetime.now().strftime("%y%m%d")
### 
###         filename_without_ext = os.path.splitext(os.path.basename(file_path))[0]
###         new_file_name = f"{filename_without_ext}_{date_str}_{sha256_hash}.pkl"
###         new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
###         
###         PickleIO._rename_file(file_path, new_file_path)
###     
###     @staticmethod
###     def load_from_pickle(file_path: str):
###         """ load pickle from file and check hash (signature from filename)
###         """
###         sha256_hash_loadfile = PickleIO._get_file_hash(file_path)
###         sha256_hash_signature = os.path.basename(file_path).split("_")[-1].split(".")[0]
###         
###         if sha256_hash_loadfile != sha256_hash_signature:
###             raise ValueError("File hash does not match")
###         else:
###             print(f"File hash checking : {sha256_hash_loadfile} : passed ")
###         
###         return PickleIO._pickle_load(file_path)