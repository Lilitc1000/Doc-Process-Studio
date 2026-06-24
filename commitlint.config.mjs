export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'header-max-length': [2, 'always', 100],
    'scope-enum': [
      2,
      'always',
      ['frontend', 'backend', 'chat', 'skill', 'incident-report', 'knowledge-base', 'auth', 'infra'],
    ],
    'scope-empty': [2, 'never'],
  },
};
