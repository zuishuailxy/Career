from huggingface_hub import snapshot_download
import os

# 1. 设置镜像加速（解决你之前的下载不成功问题）
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_ENDPOINT'] = 'https://hf-mirror.com'

# 2. 自动下载所有必要文件（包括你截图里的所有关键文件）
# 注意：repo_id 根据你截图路径填写，这里以 all-MiniLM-L6-v2 为例
snapshot_download(
    repo_id="sentence-transformers/all-MiniLM-L6-v2",  # 请替换为你实际的模型 ID
    local_dir="./models/all-MiniLM-L6-v2",            # 本地保存路径
    local_dir_use_symlinks=False,                     # 直接存文件，不用软链接
    resume_download=True,                             # 支持断点续传
    ignore_patterns=["*.h5", "*.ot", "*.bin"],        # 忽略旧格式权重（如 tf_model.h5, pytorch_model.bin）
)