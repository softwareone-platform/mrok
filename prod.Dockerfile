FROM python:3.14-slim

# The uv installer requires curl (and certificates) to download the release archive
RUN apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl vim libprotobuf-c1 build-essential; \
    apt-get autoremove --purge -y; \
    apt-get clean -y; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the uv installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1


RUN echo 'alias pip="uv pip"' >> ~/.bashrc

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN uv sync --frozen --no-dev

RUN apt-get purge -y --auto-remove build-essential; \
    apt-get clean -y; \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Running gunicorn with Uvicorn workers
CMD []
