import Conf from 'conf';

interface TerragonConfig {
  apiToken?: string;
  apiUrl: string;
  defaultAgent: string;
}

export const store = new Conf<TerragonConfig>({
  projectName: 'terragon-cli',
  defaults: {
    apiUrl: 'https://api.terragonlabs.com',
    defaultAgent: 'claude',
  },
});

export function getApiToken(): string | undefined {
  return store.get('apiToken');
}

export function setApiToken(token: string): void {
  store.set('apiToken', token);
}

export function getApiUrl(): string {
  return store.get('apiUrl');
}

export function setApiUrl(url: string): void {
  store.set('apiUrl', url);
}

export function getDefaultAgent(): string {
  return store.get('defaultAgent');
}

export function isAuthenticated(): boolean {
  return !!getApiToken();
}
