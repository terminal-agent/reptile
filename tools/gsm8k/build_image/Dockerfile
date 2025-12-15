
FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620

RUN mkdir -p /root/.config/terminal-agent /tmp/autopilot

RUN mkdir -p /testbed


# Automatically activate the virtual environment
RUN echo "source /opt/venv/bin/activate" > /root/.bashrc

COPY ./setup_env.sh /root/
RUN sed -i -e 's/\r$//' /root/setup_env.sh
RUN chmod +x /root/setup_env.sh
RUN /bin/bash /root/setup_env.sh

WORKDIR /testbed/
