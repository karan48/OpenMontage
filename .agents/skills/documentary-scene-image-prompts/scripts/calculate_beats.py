#!/usr/bin/env python3
"""Calculate how many image beats a documentary scene needs, given its voiceover duration.

Documentary-style narrated video reads comfortably at roughly one new image every
4-6 seconds of screen time (images are typically stretched further with a Ken Burns
zoom/pan). This script turns a scene duration into a beat count and per-beat duration
that stays inside that comfortable band, so scene pacing is consistent across a project.

Usage:
    python calculate_beats.py --duration 55
    python calculate_beats.py --duration 55 --target 4.5
    python calculate_beats.py --duration 30 --min 4 --max 6
"""
import argparse


def calculate_beats(duration_seconds: float, target_seconds: float = 5.0,
                     min_seconds: float = 4.0, max_seconds: float = 6.0):
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if min_seconds <= 0 or max_seconds <= 0 or min_seconds > max_seconds:
        raise ValueError("min_seconds and max_seconds must be positive with min <= max")

    raw_beats = round(duration_seconds / target_seconds)
    beats = max(1, raw_beats)
    per_beat = duration_seconds / beats

    # Nudge the beat count until per-beat duration lands in the comfortable range.
    while per_beat > max_seconds:
        beats += 1
        per_beat = duration_seconds / beats
    while per_beat < min_seconds and beats > 1:
        beats -= 1
        per_beat = duration_seconds / beats

    return beats, round(per_beat, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--duration", type=float, required=True,
                         help="Scene duration in seconds")
    parser.add_argument("--target", type=float, default=5.0,
                         help="Target seconds per image (default 5)")
    parser.add_argument("--min", dest="min_seconds", type=float, default=4.0,
                         help="Minimum comfortable seconds per image (default 4)")
    parser.add_argument("--max", dest="max_seconds", type=float, default=6.0,
                         help="Maximum comfortable seconds per image (default 6)")
    args = parser.parse_args()

    beats, per_beat = calculate_beats(args.duration, args.target,
                                       args.min_seconds, args.max_seconds)
    covered = beats * per_beat
    print(f"{beats} images, ~{per_beat} sec each "
          f"(covers {covered:.1f}s of a {args.duration:.0f}s scene)")


if __name__ == "__main__":
    main()
