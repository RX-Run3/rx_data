FROM quay.io/fedora/python-313
USER 0
WORKDIR /workspace
RUN  curl -fsSL https://pixi.sh/install.sh | sh
ENV  PATH="$HOME/.pixi/bin:${PATH}"
COPY pixi.toml pixi.lock ./
RUN  pixi install --frozen -e ci-cd
COPY src/             ./src
RUN pixi run --as-is -e ci-cd sh -c 'uv pip install --no-deps $(for d in src/*/; do printf -- "-e %s " "$d"; done)'
CMD  ["pixi", "shell", "-e", "ci-cd"]
