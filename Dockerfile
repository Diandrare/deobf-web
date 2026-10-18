FROM python:3.12-slim AS luau
RUN apt-get update && apt-get install -y --no-install-recommends git cmake g++ make && rm -rf /var/lib/apt/lists/*
COPY engine /engine
RUN cd /engine && python build_luau.py --portable
FROM python:3.12-slim
WORKDIR /app
COPY . .
COPY --from=luau /engine/bin /app/engine/bin
ENV DEOBF_TIMEOUT=600 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
CMD ["python", "server.py"]
