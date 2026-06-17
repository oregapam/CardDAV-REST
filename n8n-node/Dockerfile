FROM n8nio/n8n:latest

USER root

RUN mkdir -p /home/node/packages/n8n-nodes-carddav-rest
COPY package.json /home/node/packages/n8n-nodes-carddav-rest/
COPY dist/        /home/node/packages/n8n-nodes-carddav-rest/dist/
RUN chown -R node:node /home/node/packages

USER node

ENV N8N_CUSTOM_EXTENSIONS=/home/node/packages
