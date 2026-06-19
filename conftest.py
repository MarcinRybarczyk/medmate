"""pytest configuration for MedMate tests.

- Puts the repo root on sys.path so `import mcp_server` / `from agent import ...`
  work when tests live under tests/.
- Sets a dummy GOOGLE_API_KEY so importing agent.py (which constructs ADK agents)
  never needs a real key. This is a literal test placeholder, NOT a secret.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("GOOGLE_API_KEY", "test-dummy-not-a-real-key")
