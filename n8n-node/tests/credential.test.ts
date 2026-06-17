import { CardDavRestApi } from '../credentials/CardDavRestApi.credentials';

describe('CardDavRestApi credential', () => {
  const cred = new CardDavRestApi();

  it('has name cardDavRestApi', () => {
    expect(cred.name).toBe('cardDavRestApi');
  });

  it('has displayName CardDAV REST API', () => {
    expect(cred.displayName).toBe('CardDAV REST API');
  });

  it('has baseUrl and apiKey fields', () => {
    const fieldNames = cred.properties.map((p) => p.name);
    expect(fieldNames).toContain('baseUrl');
    expect(fieldNames).toContain('apiKey');
  });

  it('apiKey field is a password field', () => {
    const apiKeyField = cred.properties.find((p) => p.name === 'apiKey');
    expect(apiKeyField?.typeOptions?.password).toBe(true);
  });
});
