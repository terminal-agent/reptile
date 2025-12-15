FROM ubuntu:22.04

# Install necessary packages
RUN apt-get update \
    && apt-get install -y \
    python3.11 python3.11-venv python3.11-distutils python3.11-dev \
    python3-pip \
    sudo \
    python3.11 \
    openssh-server \
    vim \
    nano \
    git \
    curl \
    wget \
    zsh \
    tmux \
    locales \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3


# Set up localization
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Expose SSH port
EXPOSE 22

# Start SSH service
ENTRYPOINT service ssh restart && sleep infinity
