# Dockerfile
FROM python:3.11-slim

# set workdir
WORKDIR /app

# install system deps for build tools if needed
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc ca-certificates graphviz libgraphviz-dev && \
    rm -rf /var/lib/apt/lists/*

# copy only requirements first (for caching)
COPY requirements.txt .

# install python deps
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY certs/*.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates

# copy the rest of the code
COPY . .



# expose Streamlit’s default port
# EXPOSE 8501

# # run your app
# CMD ["python", "-m", "src.main"]

EXPOSE 8000
EXPOSE 8001
EXPOSE 8501

# Make sure it’s executable
RUN chmod +x ./entrypoint.sh

# Use it as the container’s entrypoint
ENTRYPOINT ["./entrypoint.sh"]
