export function readLocalStorage(key: string): string | null {
  try {
    const storage = globalThis.localStorage
    if (!storage || typeof storage.getItem !== 'function') {
      return null
    }
    return storage.getItem(key)
  } catch {
    return null
  }
}

export function writeLocalStorage(key: string, value: string): void {
  try {
    const storage = globalThis.localStorage
    if (!storage || typeof storage.setItem !== 'function') {
      return
    }
    storage.setItem(key, value)
  } catch {
    // ignore storage write errors
  }
}
