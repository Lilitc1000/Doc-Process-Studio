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
          name: 'incident-report-list',
          component: () =>
            import('../views/incident-report/list/IncidentReportListView.vue'),
          meta: { requiresAuth: true, pageTitle: '事故报告管理' },
        },
        {
          path: '/incident-report/create',
          name: 'incident-report-create',
          component: () =>
            import('../views/incident-report/create/IncidentReportCreateView.vue'),
          meta: { requiresAuth: true, pageTitle: '新建事故报告' },
        },
        {
          path: '/incident-report/analytics',
          name: 'incident-report-analytics',
          component: () =>
            import('../views/incident-report/analytics/IncidentReportAnalyticsView.vue'),
          meta: { requiresAuth: true, pageTitle: '统计分析' },
        },
        {
          path: '/incident-report/roles',
          name: 'incident-report-roles',
          component: () =>
            import('../views/incident-report/roles/RoleManagementView.vue'),
          meta: { requiresAuth: true, pageTitle: '角色权限管理' },
        },
        {
          path: '/incident-report/:id/audit',
          name: 'incident-report-audit',
          component: () =>
            import('../views/incident-report/audit/IncidentReportAuditView.vue'),
          meta: { requiresAuth: true, pageTitle: '审核报告' },
        },
        {
          path: '/incident-report/:id/edit',
          name: 'incident-report-edit',
          component: () =>
            import('../views/incident-report/edit/IncidentReportEditView.vue'),
          meta: { requiresAuth: true, pageTitle: '编辑报告' },
        },
        {
          path: '/incident-report/:id',
          name: 'incident-report-detail',
          component: () =>
            import('../views/incident-report/detail/IncidentReportDetailView.vue'),
          meta: { requiresAuth: true, pageTitle: '报告详情' },
        },
        {
          path: '/settings',
          name: 'settings',
          component: () => import('../views/settings/SettingsView.vue'),
        },
        {
          path: '/:pathMatch(.*)*',
          name: 'not-found',
          component: () => import('../views/NotFoundView.vue'),
          meta: { requiresAuth: true },
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
