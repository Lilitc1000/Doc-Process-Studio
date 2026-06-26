export default {
  'backend/{src,tests}/**/*.py': (filenames) => {
    const relativeFiles = filenames.map((f) => f.replace(/^backend\//, ''));
    return [
      `sh -c 'cd backend && env ENV=dev uv run --no-sync ruff check --fix ${relativeFiles.join(' ')}'`,
      `sh -c 'cd backend && env ENV=dev uv run --no-sync ruff format ${relativeFiles.join(' ')}'`,
    ];
  },
  'frontend/{src,tests}/**/*.{ts,vue}': (filenames) => {
    const relativeFiles = filenames.map((f) => f.replace(/^frontend\//, ''));
    return [
      `sh -c 'cd frontend && npx eslint --fix ${relativeFiles.join(' ')}'`,
      `sh -c 'cd frontend && npx prettier --write ${relativeFiles.join(' ')}'`,
    ];
  },
  'frontend/{src,tests}/**/*.{css,html,json,md}': (filenames) => {
    const relativeFiles = filenames.map((f) => f.replace(/^frontend\//, ''));
    return [`sh -c 'cd frontend && npx prettier --write ${relativeFiles.join(' ')}'`];
  },
};
