#!/usr/bin/env python3
"""Download LoRA models from HuggingFace to local storage.

Usage:
    python scripts/download_loras.py           # Download all LoRAs
    python scripts/download_loras.py watercolor  # Download specific LoRA
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from huggingface_hub import hf_hub_download, list_repo_files
from app.config import LORA_CONFIGS, LORA_LOCAL_DIR


def download_lora(lora_key: str, force: bool = False) -> str | None:
    """Download a LoRA from HuggingFace to local storage.

    Args:
        lora_key: The LoRA identifier from LORA_CONFIGS
        force: Re-download even if file exists

    Returns:
        Local path to downloaded file, or None if failed
    """
    if lora_key not in LORA_CONFIGS:
        print(f"Unknown LoRA key: {lora_key}")
        print(f"Available: {', '.join(LORA_CONFIGS.keys())}")
        return None

    config = LORA_CONFIGS[lora_key]
    lora_id = config.get("lora_id")

    if not lora_id or "TODO:" in lora_id:
        print(f"LoRA '{lora_key}' has no valid HuggingFace ID: {lora_id}")
        return None

    # Create local directory
    local_dir = Path(LORA_LOCAL_DIR)
    local_dir.mkdir(parents=True, exist_ok=True)

    # Determine local filename
    local_path = local_dir / f"{lora_key}.safetensors"

    if local_path.exists() and not force:
        print(f"LoRA '{lora_key}' already exists at {local_path}")
        return str(local_path)

    print(f"Downloading LoRA '{lora_key}' from {lora_id}...")

    try:
        # List files in the repo to find the .safetensors file
        files = list_repo_files(lora_id)
        safetensor_files = [f for f in files if f.endswith('.safetensors')]

        if not safetensor_files:
            # Try .bin files as fallback
            bin_files = [f for f in files if f.endswith('.bin') and 'pytorch' in f.lower()]
            if bin_files:
                target_file = bin_files[0]
                local_path = local_dir / f"{lora_key}.bin"
            else:
                print(f"No .safetensors or .bin files found in {lora_id}")
                print(f"Available files: {files[:10]}...")
                return None
        else:
            # Prefer the largest safetensors file (usually the main one)
            target_file = safetensor_files[0]
            if len(safetensor_files) > 1:
                print(f"Multiple safetensors found: {safetensor_files}")
                print(f"Using: {target_file}")

        # Download the file
        downloaded_path = hf_hub_download(
            repo_id=lora_id,
            filename=target_file,
            local_dir=str(local_dir),
            local_dir_use_symlinks=False,
        )

        # Rename to our standard naming
        downloaded = Path(downloaded_path)
        if downloaded.name != local_path.name:
            downloaded.rename(local_path)
            print(f"Renamed {downloaded.name} -> {local_path.name}")

        print(f"Downloaded to: {local_path}")
        print(f"Size: {local_path.stat().st_size / 1024 / 1024:.1f} MB")
        return str(local_path)

    except Exception as e:
        print(f"Failed to download LoRA '{lora_key}': {e}")
        return None


def download_all(force: bool = False):
    """Download all configured LoRAs."""
    results = {}

    for lora_key in LORA_CONFIGS:
        print(f"\n{'='*50}")
        result = download_lora(lora_key, force=force)
        results[lora_key] = "OK" if result else "FAILED"

    print(f"\n{'='*50}")
    print("Summary:")
    for key, status in results.items():
        print(f"  {key}: {status}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download LoRA models from HuggingFace")
    parser.add_argument("lora_key", nargs="?", help="Specific LoRA to download (default: all)")
    parser.add_argument("--force", "-f", action="store_true", help="Re-download even if exists")
    parser.add_argument("--list", "-l", action="store_true", help="List available LoRAs")

    args = parser.parse_args()

    if args.list:
        print("Available LoRAs:")
        for key, config in LORA_CONFIGS.items():
            print(f"  {key}:")
            print(f"    Name: {config.get('name')}")
            print(f"    ID: {config.get('lora_id')}")
            print(f"    Compatible: {', '.join(config.get('compatible_models', []))}")
        sys.exit(0)

    if args.lora_key:
        download_lora(args.lora_key, force=args.force)
    else:
        download_all(force=args.force)
