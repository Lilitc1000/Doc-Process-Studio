import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/auth/LoginView.vue'),
      meta: { requiresAuth: false, hideForAuth: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/auth/RegisterView.vue'),
      meta: { requiresAuth: false, hideForAuth: true },
    },
    {
      path: '/',
      component: () => import('../layouts/DefaultLayout.vue'),
      meta: { requiresAuth: true },
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

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  if (!authStore.isAuthenticated && authStore.refreshToken) {
    await authStore.refreshAccessToken();
  }

  if (authStore.isAuthenticated && !authStore.userInfo) {
    await authStore.fetchUserInfo();
  }

  const requiresAuth = to.matched.some((r) => r.meta.requiresAuth);
  const hideForAuth = to.matched.some((r) => r.meta.hideForAuth);

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } });
  } else if (hideForAuth && authStore.isAuthenticated) {
    next({ name: 'home' });
  } else {
    next();
  }
});

export default router;
