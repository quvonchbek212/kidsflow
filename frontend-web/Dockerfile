# === KIDSFLOW frontend image (Next.js standalone) ===
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm install

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* o'zgaruvchilar build vaqtida JS bundle ichiga yoziladi — runtime
# `environment:` ularga ta'sir qilmaydi. Standart qiymat nisbiy yo'l: brauzer
# so'rovi frontend turgan domenga boradi va nginx uni backendga uzatadi.
ARG NEXT_PUBLIC_API_BASE_URL=/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
