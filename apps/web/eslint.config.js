import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

const typescriptFiles = ['**/*.{ts,tsx}']
const reactFiles = ['**/*.{jsx,tsx}']

export default [
  {
    ignores: ['dist'],
  },
  {
    ...js.configs.recommended,
    files: ['**/*.{js,mjs,cjs}'],
    languageOptions: {
      globals: globals.node,
    },
  },
  ...tseslint.configs.recommended.map((config) => ({
    ...config,
    files: typescriptFiles,
  })),
  {
    ...react.configs.flat.recommended,
    files: reactFiles,
    languageOptions: {
      ...react.configs.flat.recommended.languageOptions,
      globals: globals.browser,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
  },
  {
    ...react.configs.flat['jsx-runtime'],
    files: reactFiles,
  },
  {
    ...reactHooks.configs.flat.recommended,
    files: reactFiles,
  },
  {
    ...reactRefresh.configs.vite,
    files: reactFiles,
    rules: {
      ...reactRefresh.configs.vite.rules,
      'react-refresh/only-export-components': ['error', { allowConstantExport: true }],
    },
  },
  prettier,
]
