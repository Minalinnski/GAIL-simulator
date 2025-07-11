# src/infrastructure/output/s3_service.py
import os
import boto3
from botocore.exceptions import ClientError
from typing import Union

class S3Service:
    def __init__(self, bucket: str, region: str, prefix: str):
        self.bucket = bucket
        self.prefix = prefix.strip("/")

        # 如果运行在带 IAM Role 的 EC2 上，这里不需要显式传 creds
        self.client = boto3.client("s3", region_name=region)

    def _make_key(self, rel_path: str) -> str:
        """
        构造S3 key，确保路径正确
        rel_path应该是相对于simulation目录的路径
        """
        # 移除开头的斜杠，确保路径格式正确
        rel_path = rel_path.lstrip("/")
        return os.path.join(self.prefix, rel_path).replace("\\", "/")

    def upload_file(self, local_path: str, rel_path: str) -> None:
        """
        上传本地文件到S3
        
        Args:
            local_path: 本地文件路径
            rel_path: S3中的相对路径（相对于prefix）
        """
        key = self._make_key(rel_path)
        try:
            self.client.upload_file(local_path, self.bucket, key)
            # 可根据需要打印日志
        except ClientError as e:
            raise RuntimeError(f"S3 上传失败: {e}")
    
    def upload_bytes(self, data: Union[bytes, str], rel_path: str) -> None:
        """
        直接上传字节数据到S3，不保存本地文件
        
        Args:
            data: 要上传的数据（bytes或string）
            rel_path: S3中的相对路径（相对于prefix）
        """
        key = self._make_key(rel_path)
        try:
            # 如果是字符串，转换为bytes
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data
            )
        except ClientError as e:
            raise RuntimeError(f"S3 字节上传失败: {e}")