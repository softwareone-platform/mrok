FROM python:3.12

# The uv installer requires curl (and certificates) to download the release archive
RUN apt-get clean -y; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl vim postgresql-client netcat-openbsd libprotobuf-c1 dnsutils jq; \
    apt-get autoremove --purge -y; \
    apt-get clean -y; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*


# Install oh my bash
RUN bash -c "$(curl -fsSL https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh)"

# Install starship
RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes
RUN echo 'eval "$(starship init bash)"' >> ~/.bashrc

# Install prek
RUN curl --proto '=https' --tlsv1.2 -LsSf https://github.com/j178/prek/releases/download/v0.4.1/prek-installer.sh | sh


RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-4 | bash

# Install Claude code
RUN curl -fsSL https://claude.ai/install.sh | bash

# Run the uv installer then remove it
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

RUN echo 'alias pip="uv pip"' >> ~/.bashrc

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
