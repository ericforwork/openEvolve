"""Print YYYYMMDD_HHMMSS for OpenEvolve output subdirectory (Makefile / Windows)."""
import time

if __name__ == "__main__":
    print(time.strftime("%Y%m%d_%H%M%S"), end="")
