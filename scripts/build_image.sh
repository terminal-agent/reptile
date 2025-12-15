
# build_docker.sh
# This script builds the docker image for the autopilot

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."

# Build the docker image
docker build -t autopilot:latest -f"$PROJECT_DIR/templates/Dockerfile" "$PROJECT_DIR"
