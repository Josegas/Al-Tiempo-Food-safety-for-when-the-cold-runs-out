"""Entry point for AgentCore Runtime (direct code deployment).

It lives at the root of the deployment zip so that the `agent` package is importable.
Locally, use `make chat` instead.
"""

import os

from agent.app import app

if __name__ == "__main__":
    # AgentCore routes traffic to port 8080 inside the microVM. Never expose this port publicly.
    app.run(host=os.getenv("AGENT_HOST", "0.0.0.0"), port=8080)  # noqa: S104
