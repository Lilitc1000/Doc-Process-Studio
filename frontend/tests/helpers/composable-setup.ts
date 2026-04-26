import { createApp, h, type Plugin } from 'vue';
import { createPinia, setActivePinia } from 'pinia';

export function withSetup<T>(
  composable: () => T,
): T & { app: ReturnType<typeof createApp> } {
  let result: T;
  const app = createApp({
    setup() {
      result = composable();
      return () => h('div');
    },
  });
  const pinia = createPinia();
  app.use(pinia as Plugin);
  setActivePinia(pinia);
  app.mount(document.createElement('div'));
  return { ...result!, app } as T & { app: ReturnType<typeof createApp> };
}
