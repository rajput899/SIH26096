FROM node:22-bookworm-slim
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY --chown=node:node . .
RUN chown node:node /app
USER node
EXPOSE 3000
CMD ["npm", "run", "dev"]

