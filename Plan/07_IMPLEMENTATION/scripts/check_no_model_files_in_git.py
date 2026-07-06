import argparse
from pathlib import Path
import sys

FORBIDDEN_SUFFIXES = {
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf", ".onnx",
    ".engine", ".trt", ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".wav", ".flac", ".mp3", ".ogg", ".m4a", ".aac", ".zip", ".7z", ".rar"
}

FORBIDDEN_DIR_PARTS = {
    "models", "checkpoints", "loras", "vae", "clip", "clip_vision",
    "controlnet", "upscale_models", "ipadapter", "embeddings",
    "diffusion_models", "video_models", "audio_models", "output", "outputs",
    "cache", "_ec2sd", "sync_bundles"
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    hits = []
    for p in root.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_file():
            suffix = p.suffix.lower()
            rel_parts = {part.lower() for part in p.relative_to(root).parts}
            if suffix in FORBIDDEN_SUFFIXES or (rel_parts & FORBIDDEN_DIR_PARTS):
                hits.append(str(p.relative_to(root)))
    if hits:
        print("Forbidden model/media/runtime files found:")
        for h in hits[:200]:
            print(h)
        if len(hits) > 200:
            print(f"... {len(hits)-200} more")
        sys.exit(1)
    print("No forbidden model/media/runtime files found.")

if __name__ == "__main__":
    main()
