FROM quay.io/fedora/python-313 AS builder

USER 0
RUN dnf makecache \
    && dnf install -y gcc gcc-c++ make cmake libuuid-devel \
    && dnf install -y libuuid xrootd-client krb5-workstation \
    && dnf clean all

# ---

FROM quay.io/fedora/python-313 AS final

USER 0
WORKDIR /workspace
COPY --from=builder /opt/app-root /opt/app-root
RUN  curl -fsSL https://pixi.sh/install.sh | sh
ENV  PATH="$HOME/.pixi/bin:${PATH}"
COPY pixi.toml pixi.lock .
RUN  pixi install --frozen
COPY src/             ./src
COPY requirements.txt .
RUN  pixi run uv pip install -r requirements.txt
