import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../layouts/DefaultLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('../views/home/HomeView.vue'),
        },
        {
          path: '/chat',
          name: 'chat',
          component: () => import('../views/chat/ChatView.vue'),
        },
        {
          path: '/incident-report',
          name: 'incident-report',
          component: () =>
            import('../views/incident-report/IncidentReportView.vue'),
        },
        {
          path: '/settings',
          name: 'settings',
          component: () => import('../views/settings/SettingsView.vue'),
        },
      ],
    },
  ],
});

export default router;
