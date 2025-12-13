export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Gio',
  pageTitle: 'YC AI Cofounder',
  pageDescription: `Your AI cofounder. Building something great? Let's talk.`,

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/claro-logo.svg',
  accent: '#cf232a',
  logoDark: '/claro-logo.svg',
  accentDark: '#cf232a',
  startButtonText: 'Comenzar llamada',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
