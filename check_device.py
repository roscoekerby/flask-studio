import torch
from model_server.config import settings

print("=" * 60)
print("DEVICE AND CONFIGURATION CHECK")
print("=" * 60)

print(f"\nModel ID: {settings.MODEL_ID}")
print(f"Device Map: {settings.DEVICE_MAP}")
print(f"Dtype: {settings.DTYPE}")
print(f"Enable 4-bit: {settings.ENABLE_4BIT}")
print(f"Max New Tokens: {settings.MAX_NEW_TOKENS}")

print(f"\nPyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU Count: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"    Memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
else:
    print("\nWARNING: No CUDA/GPU detected. Model will run on CPU (very slow!)")
    print("This explains the ~287 second response time.")
    print("\nRecommendations:")
    print("1. If you have a GPU, install CUDA-enabled PyTorch:")
    print("   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
    print("2. Use 4-bit quantization to reduce memory and speed up CPU inference:")
    print("   Set ENABLE_4BIT=true environment variable")
    print("3. Consider using a smaller model or cloud GPU service")

print("\n" + "=" * 60)

# Check cache location
import os
cache_dir = os.path.expanduser("~/.cache/huggingface/hub/models--google--medgemma-4b-it")
if os.path.exists(cache_dir):
    print(f"\nModel cache found at: {cache_dir}")
    # Calculate size
    import subprocess
    try:
        result = subprocess.run(['du', '-sh', cache_dir], capture_output=True, text=True)
        print(f"Cache size: {result.stdout.strip().split()[0]}")
    except:
        print("(Size calculation failed)")
else:
    print(f"\nWARNING: Model cache not found at: {cache_dir}")
    print("Model will download on first use")

print("=" * 60)
