import time
import torch
import numpy as np
import cv2
from pathlib import Path
from torch.utils.data import DataLoader, Dataset
from PIL import Image
import sys
import json
from tqdm import tqdm

# Add properties from train_local.py
TRAIN_PATH = "/Users/conniehuang/Desktop/tt_dataset_full"
BATCH_SIZE = 16
NUM_WORKERS = 0
USE_PILLOW = True

# Add ml module path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tt_video_editor" / "ml"))
from ttnet_model import TTNet


class BenchmarkDataset(Dataset):
    def __init__(self, path, split="train", n_frames=3):
        ann_path = Path(path) / f"{split}_annotations.json"
        ann = json.load(open(ann_path))
        self.samples = []
        for a in ann:
            fps = a["frame_paths"]
            self.samples.append({"frames": fps[:n_frames], "label": 0})
        # Limit to 500 samples for quick test
        self.samples = self.samples[:500]
        print(f"Benchmark dataset: {len(self.samples)} samples", flush=True)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        frames = []
        for fp in s["frames"]:
            try:
                if USE_PILLOW:
                    img = Image.open(fp).convert("RGB")
                    img = np.array(img).astype(np.float32) / 255.0
                else:
                    img = cv2.imread(fp)
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            except:
                img = np.zeros((128, 320, 3), dtype=np.float32)
            frames.append(np.transpose(img, (2, 0, 1)))
        return torch.from_numpy(np.concatenate(frames)), 0


def benchmark():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Device: {device}", flush=True)

    # 1. Benchmark Data Loading
    print("\n--- Benchmarking Data Loading ---", flush=True)
    ds = BenchmarkDataset(TRAIN_PATH)
    loader = DataLoader(
        ds, batch_size=BATCH_SIZE, num_workers=NUM_WORKERS, persistent_workers=(NUM_WORKERS > 0)
    )

    start = time.time()
    count = 0
    for _ in loader:
        count += 1
        if count >= 5:
            break
    end = time.time()
    print(f"Data Loading (5 batches of {BATCH_SIZE}): {end - start:.4f}s", flush=True)
    print(f"Average: {(end - start) / 5:.4f} s/batch", flush=True)

    # 2. Benchmark Model (Random Data)
    print("\n--- Benchmarking GPU Compute (Random Data) ---", flush=True)
    model = TTNet(tasks=["event_spotting"]).to(device)
    model.train()
    optimizer = torch.optim.Adam(model.parameters())
    criterion = torch.nn.CrossEntropyLoss()

    # Generate random batch on GPU
    x = torch.randn(BATCH_SIZE, 9, 128, 320).to(device)
    y = torch.zeros(BATCH_SIZE, dtype=torch.long).to(device)

    # Warmup
    _ = model(x)

    start = time.time()
    for _ in range(5):
        optimizer.zero_grad()
        out = model(x)["events"]
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        # No easy synchronize for MPS, just hope for the best or use a large loop
    end = time.time()

    print(f"GPU Compute (5 iters): {end - start:.4f}s", flush=True)
    print(f"Average: {(end - start) / 5:.4f} s/batch", flush=True)


if __name__ == "__main__":
    benchmark()
