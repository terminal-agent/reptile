# start_docker.sh
# This script starts the docker container for the autopilot

# Start the docker container
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USERNAME=$(whoami)
CONTAINER_NAME=${USERNAME}_autopilot
docker run -itd \
    --name ${CONTAINER_NAME} \
    -v $HOME/.cache/autopilot/pip_cache:/root/.cache/pip \
    -v $HOME/.cache/autopilot:/root/.cache/autopilot \
    -v $HOME/.config/autopilot:/root/.config/autopilot \
    -v $HOME/.gitconfig:/root/.gitconfig:ro \
    -v $HOME/.ssh:/root/.ssh:ro \
    -v $SCRIPT_DIR/..:/root/autopilot \
    autopilot:latest

docker exec ${CONTAINER_NAME} /bin/bash -c "cd /root/autopilot && pip install -e ."
docker exec --detach-keys="ctrl-]" -it ${CONTAINER_NAME} /bin/bash
docker container kill ${CONTAINER_NAME}
echo "killing container ${CONTAINER_NAME}"
docker container rm ${CONTAINER_NAME}
echo "Container ${CONTAINER_NAME} removed"
