module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  ignorePatterns: ['dist', '*.config.*', '.eslintrc.*'],
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    warnOnUnsupportedTypeScriptVersion: false,
  },
  rules: {
    '@typescript-eslint/no-unused-vars': 'error',
  },
};
