/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL absoluta del backend. Vacío en desarrollo: el proxy de Vite se encarga. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** Versión inyectada por Vite desde package.json. */
declare const __APP_VERSION__: string;
