"""Capture a timed, full-screen Pulse 109 demo to an MP4 file.

Requires the local OpenCV and MSS packages available in the workstation runtime.
The browser and demo server must be open before recording starts.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2
import mss
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Output .mp4 path")
    parser.add_argument("--duration", type=float, default=117, help="Capture length in seconds")
    parser.add_argument("--fps", type=int, default=30, help="Output frames per second")
    parser.add_argument(
        "--monitor", type=int, default=1, help="MSS monitor index; 1 is the primary display"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.duration <= 0 or args.fps <= 0:
        raise SystemExit("duration and fps must be positive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    target_interval = 1 / args.fps
    frame_count = round(args.duration * args.fps)

    with mss.MSS() as screen:
        if args.monitor < 1 or args.monitor >= len(screen.monitors):
            raise SystemExit(f"monitor must be between 1 and {len(screen.monitors) - 1}")
        monitor = screen.monitors[args.monitor]
        size = (monitor["width"], monitor["height"])
        writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, size)
        if not writer.isOpened():
            raise SystemExit("Could not initialize MP4 encoder")
        writer.set(cv2.VIDEOWRITER_PROP_QUALITY, 95)

        print(
            f"Recording {size[0]}x{size[1]} at {args.fps} fps for "
            f"{args.duration:.0f}s -> {args.output}",
            flush=True,
        )
        start = time.perf_counter()
        try:
            for index in range(frame_count):
                frame = np.asarray(screen.grab(monitor), dtype=np.uint8)
                writer.write(cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR))
                deadline = start + (index + 1) * target_interval
                delay = deadline - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
        finally:
            writer.release()

    elapsed = time.perf_counter() - start
    file_size = args.output.stat().st_size
    print(f"Saved {frame_count} frames in {elapsed:.1f}s; file size {file_size:,} bytes")


if __name__ == "__main__":
    main()
