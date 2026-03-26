module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  ignorePatterns: ['*.config.*', '.eslintrc.*'],
  extends: [
    'eslint:recommended',
    'plugin:import/recommended',
    'plugin:import/typescript',
    'plugin:vue/vue3-recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier',
  ],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', warnOnUnsupportedTypeScriptVersion: false, },
  rules: {
    'import/order': [
      'error',
      {
        groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
        'newlines-between': 'always',
        alphabetize: { order: 'asc', caseInsensitive: true },
      },
    ],
  },
};
