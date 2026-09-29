FROM node:22.14.0-alpine AS base
ENV PNPM_HOME="/pnpm" PATH="/pnpm:${PATH}"
RUN corepack enable && corepack prepare pnpm@10.33.2 --activate

FROM base AS dependencies
WORKDIR /workspace
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile

FROM dependencies AS builder
COPY apps/web apps/web
RUN pnpm --filter @pulse109/web build

FROM node:22.14.0-alpine AS runner
ENV NODE_ENV=production HOSTNAME="0.0.0.0" PORT=3000
RUN addgroup --system --gid 10001 pulse109 \
    && adduser --system --uid 10001 --ingroup pulse109 pulse109
WORKDIR /app
COPY --from=builder --chown=pulse109:pulse109 /workspace/apps/web/.next/standalone ./
COPY --from=builder --chown=pulse109:pulse109 /workspace/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=pulse109:pulse109 /workspace/apps/web/public ./apps/web/public
USER pulse109
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
