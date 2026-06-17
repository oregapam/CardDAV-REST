import { ICredentialType, INodeProperties } from 'n8n-workflow';

export class CardDavRestApi implements ICredentialType {
  name = 'cardDavRestApi';
  displayName = 'CardDAV REST API';
  documentationUrl =
    'https://github.com/mark/CardDAV-REST#authentication';
  properties: INodeProperties[] = [
    {
      displayName: 'Base URL',
      name: 'baseUrl',
      type: 'string',
      default: 'http://localhost:8000',
      placeholder: 'http://localhost:8000',
      description: 'Base URL of the CardDAV REST adapter. No trailing slash.',
    },
    {
      displayName: 'API Key',
      name: 'apiKey',
      type: 'string',
      typeOptions: { password: true },
      default: '',
      description: 'Value sent as the X-API-Key header on every request.',
    },
  ];
}
