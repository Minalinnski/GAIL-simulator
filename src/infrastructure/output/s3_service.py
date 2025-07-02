import os
import boto3
from botocore.exceptions import ClientError

class S3Service:
    def __init__(self, bucket: str, region: str, prefix: str):
        self.bucket = bucket
        self.prefix = prefix.strip("/")

        # 如果运行在带 IAM Role 的 EC2 上，这里不需要显式传 creds
        self.client = boto3.client("s3", region_name=region)

    def _make_key(self, rel_path: str) -> str:
        # 保持本地相对路径结构
        return os.path.join(self.prefix, rel_path).replace("\\", "/")

    def upload_file(self, local_path: str, rel_path: str) -> None:
        key = self._make_key(rel_path)
        try:
            self.client.upload_file(local_path, self.bucket, key)
            # 可根据需要打印日志
        except ClientError as e:
            raise RuntimeError(f"S3 上传失败: {e}")
