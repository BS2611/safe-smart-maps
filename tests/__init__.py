import os

# Tests must never start a paid Bright Data job.
os.environ["PREFETCH_ON_STARTUP"] = "0"
