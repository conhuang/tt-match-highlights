"""
TrackNetV3 PyTorch Model Architectures for Table Tennis Ball Detection and Trajectory Inpainting.

Ported from TrackNetV3_TableTennis.
Includes:
- TrackNet: 2D Convolutional Neural Network for ball candidate heatmap prediction
- InpaintNet: 1D Temporal Convolutional Neural Network for occluded trajectory interpolation
"""

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None


if TORCH_AVAILABLE:
    class Conv2DBlock(nn.Module):
        """Conv2D + BatchNorm2d + ReLU block."""
        def __init__(self, in_dim, out_dim, **kwargs):
            super().__init__(**kwargs)
            self.conv = nn.Conv2d(in_dim, out_dim, kernel_size=3, padding='same', bias=False)
            self.bn = nn.BatchNorm2d(out_dim)
            self.relu = nn.ReLU()

        def forward(self, x):
            return self.relu(self.bn(self.conv(x)))

    class Double2DConv(nn.Module):
        """Two sequential Conv2DBlocks."""
        def __init__(self, in_dim, out_dim):
            super().__init__()
            self.conv_1 = Conv2DBlock(in_dim, out_dim)
            self.conv_2 = Conv2DBlock(out_dim, out_dim)

        def forward(self, x):
            return self.conv_2(self.conv_1(x))

    class Triple2DConv(nn.Module):
        """Three sequential Conv2DBlocks."""
        def __init__(self, in_dim, out_dim):
            super().__init__()
            self.conv_1 = Conv2DBlock(in_dim, out_dim)
            self.conv_2 = Conv2DBlock(out_dim, out_dim)
            self.conv_3 = Conv2DBlock(out_dim, out_dim)

        def forward(self, x):
            return self.conv_3(self.conv_2(self.conv_1(x)))

    class TrackNet(nn.Module):
        """
        TrackNet Architecture: U-Net style encoder-decoder network that predicts
        ball heatmaps across sequential frames.
        """
        def __init__(self, in_dim=9, out_dim=3):
            super().__init__()
            self.down_block_1 = Double2DConv(in_dim, 64)
            self.down_block_2 = Double2DConv(64, 128)
            self.down_block_3 = Triple2DConv(128, 256)
            self.bottleneck = Triple2DConv(256, 512)
            self.up_block_1 = Triple2DConv(768, 256)
            self.up_block_2 = Double2DConv(384, 128)
            self.up_block_3 = Double2DConv(192, 64)
            self.predictor = nn.Conv2d(64, out_dim, (1, 1))
            self.sigmoid = nn.Sigmoid()

        def forward(self, x):
            x1 = self.down_block_1(x)                                       # (N,  64, 288, 512)
            x = nn.MaxPool2d((2, 2), stride=(2, 2))(x1)                     # (N,  64, 144, 256)
            x2 = self.down_block_2(x)                                       # (N, 128, 144, 256)
            x = nn.MaxPool2d((2, 2), stride=(2, 2))(x2)                     # (N, 128,  72, 128)
            x3 = self.down_block_3(x)                                       # (N, 256,  72, 128)
            x = nn.MaxPool2d((2, 2), stride=(2, 2))(x3)                     # (N, 256,  36,  64)
            x = self.bottleneck(x)                                          # (N, 512,  36,  64)
            x = torch.cat([nn.Upsample(scale_factor=2)(x), x3], dim=1)      # (N, 768,  72, 128)
            x = self.up_block_1(x)                                          # (N, 256,  72, 128)
            x = torch.cat([nn.Upsample(scale_factor=2)(x), x2], dim=1)      # (N, 384, 144, 256)
            x = self.up_block_2(x)                                          # (N, 128, 144, 256)
            x = torch.cat([nn.Upsample(scale_factor=2)(x), x1], dim=1)      # (N, 192, 288, 512)
            x = self.up_block_3(x)                                          # (N,  64, 288, 512)
            x = self.predictor(x)                                           # (N,   3, 288, 512)
            return self.sigmoid(x)

    class Conv1DBlock(nn.Module):
        """Conv1D + LeakyReLU block."""
        def __init__(self, in_dim, out_dim, **kwargs):
            super().__init__(**kwargs)
            self.conv = nn.Conv1d(in_dim, out_dim, kernel_size=3, padding='same', bias=True)
            self.relu = nn.LeakyReLU()

        def forward(self, x):
            return self.relu(self.conv(x))

    class Double1DConv(nn.Module):
        """Two sequential Conv1DBlocks."""
        def __init__(self, in_dim, out_dim):
            super().__init__()
            self.conv_1 = Conv1DBlock(in_dim, out_dim)
            self.conv_2 = Conv1DBlock(out_dim, out_dim)

        def forward(self, x):
            return self.conv_2(self.conv_1(x))

    class InpaintNet(nn.Module):
        """
        InpaintNet Architecture: 1D Temporal CNN to interpolate and inpaint
        occluded or missing ball positions over a sequence of frames.
        """
        def __init__(self):
            super().__init__()
            self.down_1 = Conv1DBlock(3, 32)
            self.down_2 = Conv1DBlock(32, 64)
            self.down_3 = Conv1DBlock(64, 128)
            self.bottleneck = Double1DConv(128, 256)
            self.up_1 = Conv1DBlock(384, 128)
            self.up_2 = Conv1DBlock(192, 64)
            self.up_3 = Conv1DBlock(96, 32)
            self.predictor = nn.Conv1d(32, 2, 3, padding='same')
            self.sigmoid = nn.Sigmoid()

        def forward(self, x, m):
            x = torch.cat([x, m], dim=2)                                   # (N, L, 3)
            x = x.permute(0, 2, 1)                                         # (N, 3, L)
            x1 = self.down_1(x)                                            # (N, 32, L)
            x2 = self.down_2(x1)                                           # (N, 64, L)
            x3 = self.down_3(x2)                                           # (N, 128, L)
            x = self.bottleneck(x3)                                        # (N, 256, L)
            x = torch.cat([x, x3], dim=1)                                  # (N, 384, L)
            x = self.up_1(x)                                               # (N, 128, L)
            x = torch.cat([x, x2], dim=1)                                  # (N, 192, L)
            x = self.up_2(x)                                               # (N, 64, L)
            x = torch.cat([x, x1], dim=1)                                  # (N, 96, L)
            x = self.up_3(x)                                               # (N, 32, L)
            x = self.predictor(x)                                          # (N, 2, L)
            x = self.sigmoid(x)                                            # (N, 2, L)
            return x.permute(0, 2, 1)                                      # (N, L, 2)
else:
    class TrackNet:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required to initialize TrackNet. Install with `pip install torch`.")

    class InpaintNet:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyTorch is required to initialize InpaintNet. Install with `pip install torch`.")
