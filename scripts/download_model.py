"""
Download the Nomeda Therapist 2B FP16 model from HuggingFace.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from huggingface_hub import snapshot_download
from core.rag.config import RAGConfig

REPO = RAGConfig().model_repo
SAVE_DIR = Path(__file__).resolve().parent.parent / "models" / "nomeda-therapist-2B"


def main():
    print("=" * 55)
    print(f"  Downloading {REPO} (FP16)")
    print("=" * 55)

    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    model_path = snapshot_download(
        repo_id=REPO,
        local_dir=str(SAVE_DIR),
        local_dir_use_symlinks=False,
        resume_download=True,
        ignore_patterns=["*.pt", "optimizer.pt", "training_args.bin"],
    )

    print(f"\n[+] Model downloaded to: {model_path}")

    total_size = sum(f.stat().st_size for f in Path(model_path).rglob("*") if f.is_file())
    print(f"[+] Total size: {total_size / 1e9:.2f} GB")
    print("[+] Done")


if __name__ == "__main__":
    main()
