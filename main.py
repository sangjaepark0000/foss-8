"""Course-compatible entry point; installed users can run oss instead."""
from foss8.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
