"""
FileManager - 文件处理器
负责收集、管理和打包任务执行过程中生成的文件
"""

import os
import shutil
import zipfile
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

# 配置日志
logger = logging.getLogger(__name__)

class FileManager:
    """文件管理器 - 负责任务文件的收集、管理和打包"""
    
    def __init__(self, base_dir: str = "./task_files"):
        """
        初始化文件管理器
        
        Args:
            base_dir: 基础目录，所有任务文件都将存储在此目录下
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.task_files = {}
        
        logger.info(f"FileManager初始化完成，基础目录: {self.base_dir}")
    
    def create_task_directory(self, task_id: str, user_id: str = "default") -> Path:
        """
        为任务创建专属目录
        
        Args:
            task_id: 任务ID
            user_id: 用户ID，默认为"default"
            
        Returns:
            Path: 任务目录路径
        """
        task_dir = self.base_dir / user_id / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化任务文件记录
        if task_id not in self.task_files:
            self.task_files[task_id] = {
                "files": [],
                "metadata": {
                    "task_id": task_id,
                    "user_id": user_id,
                    "created_at": datetime.now().isoformat(),
                    "task_dir": str(task_dir)
                }
            }
        
        logger.info(f"为任务 {task_id} 创建目录: {task_dir}")
        return task_dir
    
    def register_file(self, task_id: str, file_path: str, file_type: str = "unknown", 
                     step_id: str = None, description: str = "") -> bool:
        """
        注册任务生成的文件
        
        Args:
            task_id: 任务ID
            file_path: 文件路径
            file_type: 文件类型
            step_id: 生成该文件的步骤ID
            description: 文件描述
            
        Returns:
            bool: 注册是否成功
        """
        try:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在，跳过注册: {file_path}")
                return False
            
            if task_id not in self.task_files:
                self.task_files[task_id] = {"files": [], "metadata": {}}
            
            # 获取原始文件名
            original_file_name = os.path.basename(file_path)
            
            # 如果文件类型已知但文件名没有对应后缀，添加后缀
            fixed_file_name = self._ensure_file_extension(original_file_name, file_type)
            
            # 如果文件名被修改了，需要重命名实际文件
            if fixed_file_name != original_file_name:
                file_dir = os.path.dirname(file_path)
                new_file_path = os.path.join(file_dir, fixed_file_name)
                try:
                    os.rename(file_path, new_file_path)
                    file_path = new_file_path
                    logger.info(f"文件已重命名: {original_file_name} -> {fixed_file_name}")
                except Exception as e:
                    logger.warning(f"重命名文件失败: {e}，使用原文件名")
                    fixed_file_name = original_file_name
            
            file_info = {
                "file_path": str(Path(file_path).resolve()),
                "file_name": fixed_file_name,
                "file_type": file_type,
                "file_size": os.path.getsize(file_path),
                "step_id": step_id,
                "description": description,
                "registered_at": datetime.now().isoformat()
            }
            
            self.task_files[task_id]["files"].append(file_info)
            logger.info(f"文件已注册到任务 {task_id}: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"注册文件失败: {e}")
            return False
    
    def _ensure_file_extension(self, file_name: str, file_type: str) -> str:
        """
        确保文件名包含正确的后缀名
        
        Args:
            file_name: 原始文件名
            file_type: 文件类型
            
        Returns:
            str: 包含正确后缀的文件名
        """
        if file_type == "unknown":
            return file_name
        
        # 文件类型到后缀名的映射
        extension_mapping = {
            'txt': '.txt',
            'text': '.txt',
            'py': '.py',
            'python': '.py',
            'js': '.js',
            'javascript': '.js',
            'html': '.html',
            'css': '.css',
            'md': '.md',
            'markdown': '.md',
            'json': '.json',
            'xml': '.xml',
            'csv': '.csv',
            'yml': '.yml',
            'yaml': '.yaml',
            'pdf': '.pdf',
            'png': '.png',
            'jpg': '.jpg',
            'jpeg': '.jpeg',
            'gif': '.gif'
        }
        
        expected_extension = extension_mapping.get(file_type.lower())
        if not expected_extension:
            return file_name
        
        # 检查文件名是否已经有正确的后缀
        if file_name.lower().endswith(expected_extension.lower()):
            return file_name
        
        # 检查是否有其他后缀
        name_without_ext = os.path.splitext(file_name)[0]
        if name_without_ext != file_name:
            # 如果有其他后缀，替换它
            return name_without_ext + expected_extension
        else:
            # 如果没有后缀，直接添加
            return file_name + expected_extension
    
    def collect_files_from_result(self, task_id: str, execution_result) -> List[str]:
        """
        从执行结果中收集文件
        
        Args:
            task_id: 任务ID
            execution_result: TaskExecutor的执行结果
            
        Returns:
            List[str]: 收集到的文件路径列表
        """
        collected_files = []
        registered_files = set()  # 用于跟踪已注册的文件，避免重复
        
        # 获取已经注册的文件路径
        if task_id in self.task_files:
            registered_files = {file_info["file_path"] for file_info in self.task_files[task_id]["files"]}
        
        try:
            # 从execution_result.files_generated收集
            if hasattr(execution_result, 'files_generated'):
                for file_path in execution_result.files_generated:
                    # 标准化文件路径
                    normalized_path = str(Path(file_path).resolve())
                    if normalized_path not in registered_files:
                        if self.register_file(task_id, file_path):
                            collected_files.append(file_path)
                            registered_files.add(normalized_path)
            
            # 从步骤结果中收集文件
            if hasattr(execution_result, 'results'):
                for result in execution_result.results:
                    step_result = result.get('result', {})
                    step_id = result.get('step_id')
                    
                    # 处理字典格式的结果
                    if isinstance(step_result, dict):
                        if 'file_path' in step_result:
                            file_path = step_result['file_path']
                            normalized_path = str(Path(file_path).resolve())
                            
                            # 检查是否已经注册过
                            if normalized_path not in registered_files:
                                file_type = step_result.get('file_type', 'unknown')
                                description = result.get('step_description', '')
                                
                                if self.register_file(task_id, file_path, file_type, step_id, description):
                                    collected_files.append(file_path)
                                    registered_files.add(normalized_path)
                        
                        # 处理图片生成结果
                        elif 'url' in step_result and result.get('function_name') == 'image_generation':
                            # 图片生成的结果处理逻辑
                            pass
            
            logger.info(f"任务 {task_id} 共收集到 {len(collected_files)} 个新文件")
            return collected_files
            
        except Exception as e:
            logger.error(f"收集文件失败: {e}")
            return collected_files
    
    def copy_files_to_task_directory(self, task_id: str, user_id: str = "default") -> bool:
        """
        将任务的所有文件复制到任务专属目录
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            bool: 复制是否成功
        """
        try:
            if task_id not in self.task_files:
                logger.warning(f"任务 {task_id} 没有注册的文件")
                return False
            
            task_dir = self.create_task_directory(task_id, user_id)
            copied_count = 0
            
            for file_info in self.task_files[task_id]["files"]:
                source_path = file_info["file_path"]
                target_path = task_dir / file_info["file_name"]
                
                try:
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, target_path)
                        # 更新文件信息中的路径
                        file_info["copied_path"] = str(target_path)
                        copied_count += 1
                        logger.debug(f"文件已复制: {source_path} -> {target_path}")
                    else:
                        logger.warning(f"源文件不存在: {source_path}")
                        
                except Exception as e:
                    logger.error(f"复制文件失败: {source_path} -> {target_path}, 错误: {e}")
            
            logger.info(f"任务 {task_id} 成功复制 {copied_count} 个文件到 {task_dir}")
            return copied_count > 0
            
        except Exception as e:
            logger.error(f"复制文件到任务目录失败: {e}")
            return False
    
    def create_download_package(self, task_id: str, user_id: str = "default") -> Optional[str]:
        """
        为任务创建下载包(ZIP文件)
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            Optional[str]: ZIP文件路径，失败返回None
        """
        try:
            if task_id not in self.task_files:
                logger.warning(f"任务 {task_id} 没有注册的文件")
                return None
            
            # 确保用户目录存在
            user_dir = self.base_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            zip_path = user_dir / f"{task_id}_files.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                file_count = 0
                
                # 直接从注册的文件路径添加文件到ZIP
                for file_info in self.task_files[task_id]["files"]:
                    source_path = file_info["file_path"]
                    if os.path.exists(source_path):
                        # 使用文件名作为ZIP内的路径
                        arcname = file_info["file_name"]
                        zipf.write(source_path, arcname)
                        file_count += 1
                        logger.debug(f"文件已添加到ZIP: {source_path} -> {arcname}")
                    else:
                        logger.warning(f"文件不存在，跳过: {source_path}")
                
                # 添加元数据文件
                metadata = self.get_task_metadata(task_id)
                metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)
                zipf.writestr("task_metadata.json", metadata_json)
            
            logger.info(f"任务 {task_id} 的下载包已创建: {zip_path} (包含 {file_count} 个文件)")
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"创建下载包失败: {e}")
            return None
    
    def get_task_files(self, task_id: str) -> List[Dict[str, Any]]:
        """
        获取任务的所有文件信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            List[Dict]: 文件信息列表
        """
        if task_id in self.task_files:
            return self.task_files[task_id]["files"]
        return []
    
    def get_task_metadata(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务的元数据
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务元数据
        """
        if task_id in self.task_files:
            metadata = self.task_files[task_id]["metadata"].copy()
            metadata["file_count"] = len(self.task_files[task_id]["files"])
            metadata["total_size"] = sum(f.get("file_size", 0) for f in self.task_files[task_id]["files"])
            return metadata
        return {}
    
    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务文件摘要
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务文件摘要
        """
        if task_id not in self.task_files:
            return {"error": "任务不存在"}
        
        files = self.task_files[task_id]["files"]
        metadata = self.get_task_metadata(task_id)
        
        file_types = {}
        for file_info in files:
            file_type = file_info.get("file_type", "unknown")
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        return {
            "task_id": task_id,
            "file_count": len(files),
            "total_size": metadata.get("total_size", 0),
            "file_types": file_types,
            "created_at": metadata.get("created_at"),
            "files": [
                {
                    "name": f["file_name"],
                    "type": f["file_type"],
                    "size": f["file_size"],
                    "description": f.get("description", "")
                } for f in files
            ]
        }
    
    def cleanup_task_files(self, task_id: str, user_id: str = "default") -> bool:
        """
        清理任务的所有文件
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            bool: 清理是否成功
        """
        try:
            task_dir = self.base_dir / user_id / task_id
            zip_path = self.base_dir / user_id / f"{task_id}_files.zip"
            
            # 删除任务目录
            if task_dir.exists():
                shutil.rmtree(task_dir)
                logger.info(f"任务目录已删除: {task_dir}")
            
            # 删除ZIP文件
            if zip_path.exists():
                zip_path.unlink()
                logger.info(f"ZIP文件已删除: {zip_path}")
            
            # 从内存中移除记录
            if task_id in self.task_files:
                del self.task_files[task_id]
            
            return True
            
        except Exception as e:
            logger.error(f"清理任务文件失败: {e}")
            return False


# ========== 测试函数 ==========

def test_file_manager():
    """测试FileManager功能"""
    
    print("=== FileManager 测试 ===")
    
    # 创建FileManager
    file_manager = FileManager()
    
    # 测试任务ID
    test_task_id = str(uuid.uuid4())
    test_user_id = "test_user"
    
    print(f"测试任务ID: {test_task_id}")
    
    # 1. 创建任务目录
    print("\n1. 创建任务目录")
    task_dir = file_manager.create_task_directory(test_task_id, test_user_id)
    print(f"任务目录: {task_dir}")
    
    # 2. 创建一些测试文件
    print("\n2. 创建测试文件")
    test_files = []
    
    # 创建文本文件
    text_file = task_dir / "test.txt"
    text_file.write_text("这是一个测试文件", encoding='utf-8')
    test_files.append(str(text_file))
    
    # 创建JSON文件
    json_file = task_dir / "test.json"
    json_file.write_text('{"message": "测试JSON文件"}', encoding='utf-8')
    test_files.append(str(json_file))
    
    print(f"创建了 {len(test_files)} 个测试文件")
    
    # 3. 注册文件
    print("\n3. 注册文件")
    for i, file_path in enumerate(test_files):
        file_type = "txt" if file_path.endswith(".txt") else "json"
        success = file_manager.register_file(
            test_task_id, 
            file_path, 
            file_type, 
            f"step_{i+1}", 
            f"测试文件 {i+1}"
        )
        print(f"注册文件 {os.path.basename(file_path)}: {success}")
    
    # 4. 获取任务文件信息
    print("\n4. 获取任务文件信息")
    task_files = file_manager.get_task_files(test_task_id)
    print(f"任务包含 {len(task_files)} 个文件:")
    for file_info in task_files:
        print(f"  - {file_info['file_name']} ({file_info['file_type']}, {file_info['file_size']} bytes)")
    
    # 5. 获取任务摘要
    print("\n5. 获取任务摘要")
    summary = file_manager.get_task_summary(test_task_id)
    print(f"任务摘要: {json.dumps(summary, ensure_ascii=False, indent=2)}")
    
    # 6. 创建下载包
    print("\n6. 创建下载包")
    zip_path = file_manager.create_download_package(test_task_id, test_user_id)
    print(f"下载包路径: {zip_path}")
    print(f"下载包大小: {os.path.getsize(zip_path) if zip_path and os.path.exists(zip_path) else 0} bytes")
    
    # 7. 清理测试数据
    print("\n7. 清理测试数据")
    cleanup_success = file_manager.cleanup_task_files(test_task_id, test_user_id)
    print(f"清理成功: {cleanup_success}")
    
    print("\n=== FileManager 测试完成 ===")


if __name__ == "__main__":
    test_file_manager() 