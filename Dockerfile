FROM quay.io/fedora/python-313
USER 0
WORKDIR /workspace
RUN  curl -fsSL https://pixi.sh/install.sh | sh
ENV  PATH="$HOME/.pixi/bin:${PATH}"
COPY pixi.toml pixi.lock ./
RUN  pixi install --frozen -e cpu
COPY src/             ./src
COPY requirements.txt .
RUN  pixi run -e cpu uv pip install --no-deps -r requirements.txt
CMD  ["pixi", "shell", "-e", "cpu"]
