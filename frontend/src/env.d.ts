/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue';

  const component: DefineComponent<
    Record<string, never>,
    Record<string, never>,
    unknown
  >;
  export default component;
}

declare module '*.css' {
  const cssUrl: string;
  export default cssUrl;
}

declare module 'humps' {
  export function camelizeKeys<T>(obj: T): T;
  export function decamelizeKeys<T>(obj: T): T;
  export function camelize(str: string): string;
  export function decamelize(str: string): string;
}
