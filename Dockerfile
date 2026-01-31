# AgentGraph Server Docker Image
# Usage: docker run -p 8080:8080 agentgraph

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY agentgraph/ ./agentgraph/
COPY dashboard/ ./dashboard/

# Create data directory for SQLite
RUN mkdir -p /data
ENV AGENTGRAPH_DB_PATH=/data/agentgraph.db

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run server
CMD ["python", "-m", "agentgraph.api.server"]
