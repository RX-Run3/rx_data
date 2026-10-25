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
COPY pixi.toml .
COPY src       ./src
RUN curl -fsSL https://pixi.sh/install.sh | sh \
    && source ~/.bashrc \
    && pixi install
