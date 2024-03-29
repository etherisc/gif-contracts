# [Choice] Python version (use -bullseye variants on local arm64/Apple Silicon): 3, 3.10, 3.9, 3.8, 3.7, 3.6, 3-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3.7-bullseye, 3.6-bullseye, 3-buster, 3.10-buster, 3.9-buster, 3.8-buster, 3.7-buster, 3.6-buster
ARG VARIANT=3-bullseye
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

# [Choice] Node.js version: none, lts/*, 16, 14, 12, 10
ARG NODE_VERSION="16"
RUN if [ "${NODE_VERSION}" != "none" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# install mcfly as root
RUN curl -LSfs https://raw.githubusercontent.com/cantino/mcfly/master/ci/install.sh | sh -s -- --git cantino/mcfly 

USER vscode

# Shell customizations

# 1) Install and configure starship.rs prompt
RUN curl -fsSL https://starship.rs/install.sh | sh -s -- --yes
RUN echo "eval \"\$(starship init bash)\"" >> ~/.bashrc && echo "eval \"\$(starship init zsh)\"" >> ~/.zshrc
RUN mkdir -p /home/vscode/.config/
COPY .devcontainer/starship.toml /home/vscode/.config/starship.toml

# 2) install thefuck
RUN pip3 install thefuck --user \
    && echo 'eval "$(thefuck --alias)"' >> ~/.bashrc \
    && echo 'eval "$(thefuck --alias)"' >> ~/.zshrc

# 3) install mcfly config
RUN echo 'eval "$(mcfly init zsh)"' >> ~/.zshrc \
    && touch ~/.zsh_history

RUN pip install eth-brownie

# [Optional] Uncomment this line to install global node packages.
RUN npm install -g ganache solhint prettier prettier-plugin-solidity solhint-plugin-prettier

# # download required solidity compiler
COPY .devcontainer/scripts/install_solidity.sh /tmp
RUN /tmp/install_solidity.sh

# Download openzeppelin and chainlink depedencies (large and slow)
ARG VERSION_OPEN_ZEPPELIN=4.7.3
ARG VERSION_CHAINLINK=1.6.0
RUN wget -O /tmp/v${VERSION_OPEN_ZEPPELIN}.tar.gz https://github.com/OpenZeppelin/openzeppelin-contracts/archive/refs/tags/v${VERSION_OPEN_ZEPPELIN}.tar.gz \
    && wget -O /tmp/v${VERSION_CHAINLINK}.tar.gz https://github.com/smartcontractkit/chainlink/archive/refs/tags/v${VERSION_CHAINLINK}.tar.gz
RUN mkdir -p /home/vscode/.brownie/packages/OpenZeppelin \
    && cd /home/vscode/.brownie/packages/OpenZeppelin \
    && tar xvfz /tmp/v${VERSION_OPEN_ZEPPELIN}.tar.gz \
    && mv openzeppelin-contracts-${VERSION_OPEN_ZEPPELIN} openzeppelin-contracts@${VERSION_OPEN_ZEPPELIN} \
    && mkdir -p /home/vscode/.brownie/packages/smartcontractkit \
    && cd /home/vscode/.brownie/packages/smartcontractkit \
    && tar xvfz /tmp/v${VERSION_CHAINLINK}.tar.gz \
    && mv chainlink-${VERSION_CHAINLINK} chainlink@${VERSION_CHAINLINK}

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>

# install foundry
RUN curl -L https://foundry.paradigm.xyz | bash
RUN echo 'export PATH="$PATH:/home/vscode/.foundry/bin"' >> ~/.zshrc
RUN /home/vscode/.foundry/bin/foundryup


WORKDIR /workspace
