<template>
  <section class="role-management-view">
    <div class="role-management-header">
      <base-button
        variant="ghost"
        size="sm"
        @click="router.push('/incident-report')"
      >
        <svg
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12.5 15L7.5 10L12.5 5" />
        </svg>
        返回列表
      </base-button>
      <h1>角色权限管理</h1>
      <p class="role-management-hint">
        管理员角色由系统自动分配，不支持手动添加或移除
      </p>
    </div>

    <div class="role-management-body">
      <div v-if="loading" class="role-management-loading">加载中...</div>

      <div v-else-if="users.length === 0" class="role-management-empty">
        暂无可管理的用户
      </div>

      <table v-else class="role-management-table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>当前角色</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.userId">
            <td class="role-management-username">{{ user.username }}</td>
            <td>
              <div class="role-management-tags">
                <span v-for="role in user.roles" :key="role" class="role-tag">
                  {{ roleLabel(role) }}
                  <base-button
                    type="button"
                    class="role-tag-remove"
                    variant="ghost"
                    size="sm"
                    title="移除角色"
                    @click="handleRevoke(user.userId, role)"
                  >
                    ×
                  </base-button>
                </span>
                <span v-if="user.roles.length === 0" class="role-tag-empty">
                  未分配角色
                </span>
              </div>
            </td>
            <td>
              <div class="role-management-actions">
                <base-dropdown
                  :model-value="''"
                  :options="availableRolesForUser(user)"
                  placeholder="添加角色"
                  panel-min-width="140px"
                  @update:model-value="handleAssign(user.userId, $event)"
                />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import {
  fetchUsersWithRoles,
  assignIncidentRole,
  revokeIncidentRole,
} from '../../../api/incident-report';
import type { IncidentUserWithRolesEntry } from '../../../types/incident-report/incident-report';
import { INCIDENT_ROLE_LABELS } from '../../../types/incident-report/incident-report';
import BaseButton from '../../../components/base/BaseButton.vue';
import BaseDropdown from '../../../components/base/BaseDropdown.vue';

const router = useRouter();

const users = ref<IncidentUserWithRolesEntry[]>([]);
const loading = ref(false);

const ALL_ROLE_KEYS = ['verifier', 'handler', 'reporter', 'viewer'];

const roleLabel = (role: string) => INCIDENT_ROLE_LABELS[role] ?? role;

const availableRolesForUser = (user: IncidentUserWithRolesEntry) => {
  return ALL_ROLE_KEYS.filter((r) => !user.roles.includes(r)).map((r) => ({
    value: r,
    label: roleLabel(r),
  }));
};

const loadUsers = async () => {
  loading.value = true;
  try {
    const response = await fetchUsersWithRoles();
    users.value = response.items ?? [];
  } finally {
    loading.value = false;
  }
};

const handleAssign = async (userId: string, role: string) => {
  if (!role) return;
  await assignIncidentRole({ userId, role });
  await loadUsers();
};

const handleRevoke = async (userId: string, role: string) => {
  await revokeIncidentRole(userId, role);
  await loadUsers();
};

onMounted(() => {
  loadUsers();
});
</script>

<style scoped>
.role-management-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--space-xl);
}

.role-management-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-xl);
}

.role-management-header h1 {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  margin: 0;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.role-management-hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.role-management-body {
  flex: 1;
  min-height: 0;
}

.role-management-loading,
.role-management-empty {
  text-align: center;
  padding: var(--space-2xl);
  color: var(--color-text-secondary);
}

.role-management-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg-primary);
  box-shadow: var(--shadow-card);
}

.role-management-table th {
  text-align: left;
  padding: var(--space-md) var(--space-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  border-bottom: 2px solid var(--color-border);
  font-size: var(--text-xs);
  background: var(--color-bg-secondary);
}

.role-management-table td {
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.role-management-table tr:last-child td {
  border-bottom: none;
}

.role-management-table tr:hover td {
  background: var(--color-bg-hover);
}

.role-management-username {
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.role-management-tags {
  display: flex;
  gap: var(--space-xs);
  flex-wrap: wrap;
  align-items: center;
}

.role-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--radius-full);
  background: var(--color-primary-light);
  color: var(--color-primary-hover);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border: 1px solid var(--color-primary-lighter);
}

.role-tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  border: none !important;
  background: transparent !important;
  color: var(--color-border-focus);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: var(--text-sm);
  line-height: 1;
  padding: 0 !important;
  min-height: unset !important;
  transition:
    background var(--transition-fast),
    color var(--transition-fast);
}

.role-tag-remove:hover {
  background: var(--color-primary-lighter);
  color: var(--color-primary-hover);
}

.role-tag-empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.role-management-actions {
  min-width: 7.5rem;
}

@media (max-width: 768px) {
  .role-management-table {
    font-size: var(--text-xs);
  }

  .role-management-table th,
  .role-management-table td {
    padding: var(--space-sm) var(--space-sm);
  }
}
</style>
