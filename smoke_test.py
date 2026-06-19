"""smoke_test.py — one minimal REAL Gemini call to verify the key + connectivity.

Loads GOOGLE_API_KEY from .env / the environment via python-dotenv. NEVER prints
the key. If the key is missing it aborts with a clear message (exit 2). Prints
only status: ok/error, model, latency. Errors for bad key / 403 / 429 are mapped
to plain hints.

Run:  python smoke_test.py
"""
import os
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env (gitignored) into the environment if present
except Exception:
    pass

MODEL = "gemini-2.0-flash"   # cheap/fast model; one call only


def main() -> int:
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("ABORT: GOOGLE_API_KEY is not set. Put it in .env "
              "(GOOGLE_API_KEY=...) or your environment. Never commit it.")
        return 2

    try:
        from google import genai
    except Exception as e:
        print(f"ERROR: google-genai not importable ({type(e).__name__}). "
              f"Run: pip install -r requirements.txt")
        return 1

    try:
        client = genai.Client(api_key=key)
        t0 = time.time()
        resp = client.models.generate_content(model=MODEL, contents="Reply with exactly: OK")
        dt = time.time() - t0
        reply = (getattr(resp, "text", "") or "").strip()
        print(f"OK  model={MODEL}  latency={dt:.2f}s  reply={reply!r}")
        return 0
    except Exception as e:
        low = str(e).lower()
        if "api key not valid" in low or ("invalid" in low and "key" in low):
            hint = "invalid API key"
        elif "403" in low or "permission" in low or "denied" in low:
            hint = "403 / permission denied (check key, project, or that the API is enabled)"
        elif "429" in low or "quota" in low or "resource_exhausted" in low or "rate" in low:
            hint = "429 / rate limit or quota exceeded — wait and retry"
        else:
            hint = "unexpected error"
        # Print type + hint only — never the raw exception (defensive: no key echo).
        print(f"ERROR  model={MODEL}  type={type(e).__name__}  hint={hint}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
