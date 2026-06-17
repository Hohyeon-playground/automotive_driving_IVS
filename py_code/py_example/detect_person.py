import subprocess

command = [
    "rpicam-hello",
    "-v", "2",
    "-t", "0",
    "--post-process-file", "/usr/share/rpi-camera-assets/hailo_yolov8_inference.json",
]

print("Starting AI person detection. Press Ctrl+C to stop.")

process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

try:
    for line in process.stdout:
        if not line:
            continue

        line = line.strip()

        if "Object:" in line and "person" in line:
            print("PERSON detected:", line)

except KeyboardInterrupt:
    print("\nStopping process...")

finally:
    try:
        process.terminate()
    except Exception:
        pass
    print("Process finished.")
