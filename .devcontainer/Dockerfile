# [Choice] Python version (use -bullseye variants on local arm64/Apple Silicon): 3, 3.10, 3.9, 3.8, 3.7, 3.6, 3-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3.7-bullseye, 3.6-bullseye, 3-buster, 3.10-buster, 3.9-buster, 3.8-buster, 3.7-buster, 3.6-buster
ARG VARIANT=3-bullseye
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# [Choice] Node.js version: none, lts/*, 16, 14, 12, 10
ARG NODE_VERSION="16"
RUN if [ "${NODE_VERSION}" != "none" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

USER vscode

# Install and configure starship.rs prompt
RUN curl -fsSL https://starship.rs/install.sh | sh -s -- --yes
RUN echo "eval \"\$(starship init bash)\"" >> ~/.bashrc && echo "eval \"\$(starship init zsh)\"" >> ~/.zshrc
RUN mkdir -p /home/vscode/.config/
COPY .devcontainer/starship.toml /home/vscode/.config/starship.toml

# [Optional] If your pip requirements rarely change, uncomment this section to add them to the image.
# COPY requirements.txt /tmp/pip-tmp/
RUN wget https://raw.githubusercontent.com/eth-brownie/brownie/master/requirements.txt -O /tmp/pip-requirements.txt 

RUN pip install -r /tmp/pip-requirements.txt
RUN pip install eth-brownie \
    && pip install fastapi \
    && pip install uvicorn

# [Optional] Uncomment this line to install global node packages.
RUN npm install -g ganache-cli

RUN mkdir -p /tmp/brownie-setup
WORKDIR /tmp/brownie-setup
COPY .devcontainer/get_solidity.py .

# download required solidity compiler
RUN python get_solidity.py

# Create dummy project and compile it to cache dependencies
COPY brownie-config.yaml .
RUN /home/vscode/.local/bin/brownie init dummy \
    && cd dummy \
    && cp ../brownie-config.yaml . \
    && /home/vscode/.local/bin/brownie compile --all

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>

WORKDIR /workspace
