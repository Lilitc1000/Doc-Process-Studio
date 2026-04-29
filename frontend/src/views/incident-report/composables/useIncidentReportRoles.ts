import { ref } from 'vue';
import {
  fetchUserIncidentRoles,
  fetchUserIncidentPermissions,
} from '../../../api/incident-report';

export function useIncidentReportRoles() {
  const roles = ref<string[]>([]);
  const permissions = ref<string[]>([]);
  const loading = ref(false);

  const loadRoles = async () => {
    loading.value = true;
    try {
      roles.value = await fetchUserIncidentRoles();
      permissions.value = await fetchUserIncidentPermissions();
    } finally {
      loading.value = false;
    }
  };

  const hasRole = (role: string) => roles.value.includes(role);
  const hasAnyRole = (...checkRoles: string[]) =>
    roles.value.some((r) => checkRoles.includes(r));
  const hasPermission = (permission: string) =>
    permissions.value.includes(permission);
  const hasAnyPermission = (...checkPermissions: string[]) =>
    checkPermissions.some((p) => permissions.value.includes(p));

  return {
    roles,
    permissions,
    loading,
    loadRoles,
    hasRole,
    hasAnyRole,
    hasPermission,
    hasAnyPermission,
  };
}
