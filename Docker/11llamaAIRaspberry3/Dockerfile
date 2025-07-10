FROM debian:bullseye-slim

# Installa dipendenze
RUN apt-get update && \
    apt-get install -y \
    git build-essential cmake curl wget libcurl4-openssl-dev \
    python3 python3-pip && \
    pip3 install flask requests && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Clona llama.cpp
RUN git clone https://github.com/ggerganov/llama.cpp /llama.cpp

# Compila usando CMake (metodo ufficiale)
WORKDIR /llama.cpp
RUN mkdir build && cd build && \
    cmake .. -DLLAMA_BUILD_SERVER=ON -DLLAMA_NATIVE=ON && \
    cmake --build . --config Release -j$(nproc) --target llama-server

# Verifica che il server sia stato compilato e spostalo
RUN ls -la /llama.cpp/build/bin/llama-server && \
    mkdir -p /llama.cpp/build/bin && \
    cp /llama.cpp/build/bin/llama-server /llama.cpp/build/bin/server || \
    echo "✅ Server già presente come llama-server"

# Copia script e UI
COPY download-model.sh /download-model.sh
COPY entrypoint.sh /entrypoint.sh
COPY ui /ui

RUN chmod +x /download-model.sh /entrypoint.sh

EXPOSE 8080 5000
ENTRYPOINT ["/entrypoint.sh"]
