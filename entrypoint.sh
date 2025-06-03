#!/usr/bin/env sh
# entrypoint.sh

# Start the main FastAPI app in the background
uvicorn src.backend.endpoints:app \
    --host 0.0.0.0 \
    --port 8000 &

python -m src.main

# Start the webhook listener in the foreground
# uvicorn src.webhook:wh_app \
#     --host 0.0.0.0 \
#     --port 8001

# When webhook_server exits, shut down
wait
