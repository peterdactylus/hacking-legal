image := "eqs-mcp-server"
container := "eqs-mcp"

# Build the Docker image
build:
    docker build -t {{image}} .

# Start the MCP server container (reads credentials from .env)
start:
    docker run -d \
        -p 8000:8000 \
        --env-file .env \
        --name {{container}} \
        {{image}}
    @echo "MCP server running at http://localhost:8000/sse"

# Stop and remove the container
stop:
    docker stop {{container}} && docker rm {{container}}

# Tail container logs
logs:
    docker logs -f {{container}}

# Run tests inside a temporary container
test:
    docker run --rm \
        -e EQS_CLIENT_ID=test \
        -e EQS_CLIENT_SECRET=test \
        {{image}} \
        pytest tests/ -v

# Rebuild and restart
restart: stop build start
