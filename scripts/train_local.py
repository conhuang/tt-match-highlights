#!/usr/bin/env python3
"""
Local TTNet training script for Mac with MPS acceleration.

Usage:
    python scripts/train_local.py

Checkpoints are saved after each epoch, so you can resume if interrupted.
"""

import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

# Add ml module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "tt_video_editor" / "ml"))
from ttnet_model import TTNet

# ============ Configuration ============
TRAIN_PATH = "/Users/conniehuang/Desktop/tt_dataset_full"
TEST_PATH = "/Users/conniehuang/Desktop/tt_dataset_test"
OUTPUT_PATH = "/Users/conniehuang/Desktop/tt_models"

BATCH_SIZE = 16
NUM_EPOCHS = 30
LEARNING_RATE = 1e-4
NUM_WORKERS = 4  # Set to 0 to avoid NumPy multiprocessing issues
RESUME = True


# ============ Dataset ============
class TTDataset(Dataset):
    def __init__(self, path, split="train", n_frames=3):
        ann_path = Path(path) / f"{split}_annotations.json"
        ann = json.load(open(ann_path))
        self.samples = []

        for a in ann:
            fps = a["frame_paths"]
            rs, re = a["event_labels"]["rally_start"], a["event_labels"]["rally_end"]
            for i in range(len(fps) - n_frames + 1):
                label = 1 if rs <= i <= re else 0
                self.samples.append({"frames": fps[i : i + n_frames], "label": label})

        print(f"{split}: {len(self.samples)} samples")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        frames = []
        for fp in s["frames"]:
            img = cv2.imread(fp)
            if img is None:
                img = np.zeros((128, 320, 3), dtype=np.uint8)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            frames.append(np.transpose(img, (2, 0, 1)))
        return torch.from_numpy(np.concatenate(frames)), s["label"]


def get_device():
    """Get the best available device."""
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")


def train():
    device = get_device()
    print(f"Using device: {device}")

    # Create output directory
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # Load data
    print("Loading datasets...")
    train_ds = TTDataset(TRAIN_PATH, "train")
    val_ds = TTDataset(TRAIN_PATH, "val")

    train_loader = DataLoader(
        train_ds, BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS, pin_memory=True
    )
    val_loader = DataLoader(val_ds, BATCH_SIZE, num_workers=NUM_WORKERS, pin_memory=True)

    # Model
    # Model - only use event_spotting to avoid MPS issues with BallDetectionHead
    model = TTNet(dropout_p=0.5, tasks=["event_spotting"]).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # Resume from checkpoint
    ckpt_path = Path(OUTPUT_PATH) / "checkpoint.pth"
    start_epoch, best_acc = 0, 0
    history = {"loss": [], "acc": []}

    if RESUME and ckpt_path.exists():
        print("Loading checkpoint...")
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optim"])
        start_epoch = ckpt["epoch"] + 1
        best_acc = ckpt["best"]
        history = ckpt.get("hist", history)
        print(f"Resuming from epoch {start_epoch}, best_acc={best_acc:.4f}")

    # Training loop
    print(f"\nStarting training for {NUM_EPOCHS} epochs...")
    for epoch in range(start_epoch, NUM_EPOCHS):
        model.train()
        loss_sum = 0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{NUM_EPOCHS}")
        for x, y in pbar:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()

            out = model(x)["events"]
            # Convert sigmoid output to logits
            logits = torch.log(out / (1 - out + 1e-8))
            loss = criterion(logits, y)

            loss.backward()
            optimizer.step()
            loss_sum += loss.item()

            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        # Validation
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                preds = model(x)["events"].argmax(1)
                correct += (preds == y).sum().item()
                total += y.size(0)

        val_acc = correct / total
        avg_loss = loss_sum / len(train_loader)
        scheduler.step(1 - val_acc)

        history["loss"].append(avg_loss)
        history["acc"].append(val_acc)

        print(f"Epoch {epoch + 1}: loss={avg_loss:.4f}, val_acc={val_acc:.4f}")

        # Save checkpoint
        torch.save(
            {
                "epoch": epoch,
                "model": model.state_dict(),
                "optim": optimizer.state_dict(),
                "best": max(best_acc, val_acc),
                "hist": history,
            },
            ckpt_path,
        )

        if val_acc > best_acc:
            best_acc = val_acc
            best_path = Path(OUTPUT_PATH) / "ttnet_best.pth"
            torch.save({"model_state_dict": model.state_dict(), "val_acc": val_acc}, best_path)
            print(f"  -> New best model saved! ({best_acc:.4f})")

    print(f"\nTraining complete! Best accuracy: {best_acc:.4f}")
    print(f"Model saved to: {OUTPUT_PATH}/ttnet_best.pth")


if __name__ == "__main__":
    train()
