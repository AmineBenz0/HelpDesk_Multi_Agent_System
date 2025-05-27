# Dockerfile
FROM python:3.11-slim

# set workdir
WORKDIR /app

# install system deps for build tools if needed
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc graphviz libgraphviz-dev && \
    rm -rf /var/lib/apt/lists/*

# copy only requirements first (for caching)
COPY requirements.txt .

# install python deps
RUN pip install --no-cache-dir -r requirements.txt

# copy the rest of the code
COPY . .

# expose Streamlit’s default port
EXPOSE 8501

# run your app
CMD ["python", "-m", "src.main"]
