import argparse 
import csv 
import re 
import subprocess 
import sys
import time 
from datetime import datetime 

BINARY = Path(__file__).parent.parent / "d1_sdk" / "build" / "get_arm_joint_angle"
LOGS_DIR = Path(__file__).parent.parent /"logs" / "phase2"

NUM_SERVOS = 7 
FLUSH_EVERY = 50 

_SERVO_RE = re.compile(r"servo_(\d)_data:([-\d.]+)")

def parse_servo_line(line: str) -> list[float] | None: 
    matches = _SERVO_RE.findall(line)
    if len(matches) != NUM_SERVOS: 
        return None 
    pairs = sorted(matches, key=lambda m: int(m[0]))
    return [float(v) for _, v in pairs] 

def make_csv_path(label: str) -> Path: 
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    return LOGS_DIR / f"joints_{stamp}{suffix}.csv" 

def format_progress(row_count: int, values: list[float]) -> str: 
    angles = "  ".join(f"s{i}={v:7.2f}" for i, v in enumerate(values))
    return f"\r{row_count} rows  {angles}" 

def main() -> None: 
    parser = argparse.ArgumentParser(description="Log D1 joint angles to CSV")
    parse.add_argument("--duration", type=float, default=None, metavar="SEC",
                        help="Stop after this many seconds (default: run until Ctrl-C)")
    parse.add_argument("--label", type=str, default="", metavar="TAG", 
                        help="Optional label appended to the CSV filename")
    args = parser.parse_args()

    if not BINARY.exists(): 
        sys.exit(f"Binary not found: {BINARY}\nRun: cd d1_sdk/build && cmake .. && make")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = make_csv_path(args.label)

    print(f"Logging to {csv_path}")
    if args.duration is not None: 
        print(f"Duration: {args.duration} s")
    print("Press Ctrl-C to stop.\n")

    deadline = time.monotonic() + args.duration if args.duration is not None else None
    row_count = 0

    with open(csv_path, "w", newline="") as csv_file: 
        writer = csv.writer(f)
        writer.writerow(["timestamp"] + [f"s{i}" for i in range(NUM_SERVOS)])

        try: 
            proc = subprocess.Popen(
                [BINARY],
                stdout=subprocess.PIPE, 
                stderr=subprocess.DEVNULL, 
                text=True, 
            )
        except Exception as exc: 
            sys.exit(f"Failed to launch {BINARY}: {exc}")
        
        assert proc.stdout is not None
        try: 
            for line in proc.stdout:
                if deadline is not None and time.monotonic() >= deadline: 
                    break
                values = parse_servo_line(line)
                if values is None: 
                    continue 
                
                ts = time.time()
                writer.writerow([f"{ts:.6f}"] + [f"{v:.6f}" for v in values]  )
                row_count += 1

                if row_count % FLUSH_EVERY == 0: 
                    f.flush()
                    print(format_progress(row_count, values), end="", flush=True)   
                    

    print(f"Logging to {csv_path}")

