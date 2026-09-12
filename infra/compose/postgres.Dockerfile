FROM postgis/postgis:16-3.5

ARG PGVECTOR_COMMIT=2627c5ff775ae6d7aef0c430121ccf857842d2f2
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        postgresql-server-dev-16 \
    && git clone --filter=blob:none https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && git -C /tmp/pgvector checkout --detach "${PGVECTOR_COMMIT}" \
    && make -C /tmp/pgvector \
    && make -C /tmp/pgvector install \
    && rm -rf /tmp/pgvector /var/lib/apt/lists/*

COPY infra/compose/init/001-extensions.sql /docker-entrypoint-initdb.d/001-extensions.sql

