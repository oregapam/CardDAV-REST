FROM n8nio/n8n:latest

USER root

COPY package.json /home/node/.n8n/custom/n8n-nodes-carddav-rest/
COPY dist/        /home/node/.n8n/custom/n8n-nodes-carddav-rest/dist/

RUN chown -R node:node /home/node/.n8n/custom

USER node

ENV N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom
