import { ref } from 'vue';
import { fetchUserIncidentRoles } from '../../../api/incident-report';

export function useIncidentReportRoles() {
  const roles = ref<string[]>([]);
  const loading = ref(false);

  const loadRoles = async () => {
    loading.value = true;
    try {
      roles.value = await fetchUserIncidentRoles();
    } finally {
      loading.value = false;
    }
  };

  const hasRole = (role: string) => roles.value.includes(role);
  const hasAnyRole = (...checkRoles: string[]) =>
    roles.value.some((r) => checkRoles.includes(r));

  return {
    roles,
    loading,
    loadRoles,
    hasRole,
    hasAnyRole,
  };
}
