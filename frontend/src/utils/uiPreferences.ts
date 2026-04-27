import { readLocalStorage, writeLocalStorage } from './storage'

export type AppTheme = 'default' | 'minimal' | 'contrast'

export const DEMO_MODE_STORAGE_KEY = 'gradebook-demo-mode'
export const APP_THEME_STORAGE_KEY = 'gradebook-app-theme'
export const UI_PREFERENCES_EVENT = 'gradebook-ui-preferences-changed'

export function isDemoModeEnabled(): boolean {
  return readLocalStorage(DEMO_MODE_STORAGE_KEY) === 'enabled'
}

export function setDemoModeEnabled(enabled: boolean): void {
  writeLocalStorage(DEMO_MODE_STORAGE_KEY, enabled ? 'enabled' : 'disabled')
  emitUiPreferencesChanged()
}

export function readAppTheme(): AppTheme {
  const cached = readLocalStorage(APP_THEME_STORAGE_KEY)
  if (cached === 'minimal' || cached === 'contrast') return cached
  return 'default'
}

export function setAppTheme(theme: AppTheme): void {
  writeLocalStorage(APP_THEME_STORAGE_KEY, theme)
  emitUiPreferencesChanged()
}

export function emitUiPreferencesChanged(): void {
  globalThis.dispatchEvent?.(new CustomEvent(UI_PREFERENCES_EVENT))
}
