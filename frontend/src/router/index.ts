import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@modules/auth';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@modules/auth/views/LoginView.vue'),
      meta: { requiresAuth: false, hideForAuth: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@modules/auth/views/RegisterView.vue'),
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
          component: () => import('@modules/home/views/HomeView.vue'),
        },
        {
          path: '/chat',
          name: 'chat',
          component: () => import('@modules/chat/views/ChatView.vue'),
        },
        {
          path: '/incident-report',
          name: 'incident-report-list',
          component: () =>
            import('@modules/incident-report/views/list/IncidentReportListView.vue'),
          meta: { requiresAuth: true, pageTitle: '事故报告管理' },
        },
        {
          path: '/incident-report/create',
          name: 'incident-report-create',
          component: () =>
            import('@modules/incident-report/views/create/IncidentReportCreateView.vue'),
          meta: { requiresAuth: true, pageTitle: '新建事故报告' },
        },
        {
          path: '/incident-report/analytics',
          name: 'incident-report-analytics',
          component: () =>
            import('@modules/incident-report/views/analytics/IncidentReportAnalyticsView.vue'),
          meta: { requiresAuth: true, pageTitle: '统计分析' },
        },
        {
          path: '/incident-report/roles',
          name: 'incident-report-roles',
          component: () =>
            import('@modules/incident-report/views/roles/RoleManagementView.vue'),
          meta: { requiresAuth: true, pageTitle: '角色权限管理' },
        },
        {
          path: '/incident-report/:id/edit',
          name: 'incident-report-edit',
          component: () =>
            import('@modules/incident-report/views/edit/IncidentReportEditView.vue'),
          meta: { requiresAuth: true, pageTitle: '编辑报告' },
        },
        {
          path: '/incident-report/:id',
          name: 'incident-report-detail',
          component: () =>
            import('@modules/incident-report/views/detail/IncidentReportDetailView.vue'),
          meta: { requiresAuth: true, pageTitle: '报告详情' },
        },
        {
          path: '/settings',
          name: 'settings',
          component: () => import('@modules/settings/views/SettingsView.vue'),
        },
        {
          path: '/knowledge-base',
          name: 'knowledge-base-list',
          component: () =>
            import('@modules/knowledge-base/views/KnowledgeBaseListView.vue'),
          meta: { requiresAuth: true, pageTitle: '知识库' },
        },
        {
          path: '/knowledge-base/:id',
          name: 'knowledge-base-detail',
          component: () =>
            import('@modules/knowledge-base/views/KnowledgeBaseDetailView.vue'),
          meta: { requiresAuth: true, pageTitle: '知识库项目' },
        },
        {
          path: '/:pathMatch(.*)*',
          name: 'not-found',
          component: () => import('@shared/views/NotFoundView.vue'),
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
