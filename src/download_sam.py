import os
import urllib.request

MODEL_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
MODEL_PATH = "models/sam_vit_b_01ec64.pth"

def download_model():
    os.makedirs("models", exist_ok=True)
    
    if os.path.exists(MODEL_PATH):
        print(f"模型文件已存在: {MODEL_PATH}")
        return
    
    print(f"正在下载SAM模型: {MODEL_URL}")
    print("这可能需要几分钟...")
    
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"模型下载完成: {MODEL_PATH}")
    except Exception as e:
        print(f"下载失败: {e}")
        print("请手动下载模型文件并放置到 models/ 目录下")
        print(f"下载地址: {MODEL_URL}")

if __name__ == "__main__":
    download_model()