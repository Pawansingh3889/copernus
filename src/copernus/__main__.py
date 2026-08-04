"""`python -m copernus` — the dev server. Production runs uvicorn directly."""

from __future__ import annotations

import sys

import uvicorn


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] != "serve":
        print(f"Unknown command {sys.argv[1]!r}. Try: python -m copernus serve", file=sys.stderr)
        return 2
    uvicorn.run("copernus.app:create_app", factory=True, port=8010, reload=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
