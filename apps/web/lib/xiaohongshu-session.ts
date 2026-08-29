export const XIAOHONGSHU_LOGIN_RECHECK_MS = 5 * 60_000;

const XIAOHONGSHU_LOGIN_CACHE_KEY = "growthagent:xiaohongshu-login-confirmed-at";

export interface SessionStorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export interface XiaohongshuLoginConfirmation {
  confirmedAt: number;
  fresh: boolean;
}

function browserSessionStorage(): SessionStorageLike | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function readXiaohongshuLoginConfirmation(
  storage: SessionStorageLike | null = browserSessionStorage(),
  now = Date.now(),
): XiaohongshuLoginConfirmation | null {
  if (!storage) return null;
  try {
    const confirmedAt = Number(storage.getItem(XIAOHONGSHU_LOGIN_CACHE_KEY));
    if (!Number.isFinite(confirmedAt) || confirmedAt <= 0 || confirmedAt > now + 60_000) {
      return null;
    }
    return {
      confirmedAt,
      fresh: now - confirmedAt < XIAOHONGSHU_LOGIN_RECHECK_MS,
    };
  } catch {
    return null;
  }
}

export function rememberXiaohongshuLogin(
  storage: SessionStorageLike | null = browserSessionStorage(),
  confirmedAt = Date.now(),
) {
  if (!storage) return;
  try {
    storage.setItem(XIAOHONGSHU_LOGIN_CACHE_KEY, String(confirmedAt));
  } catch {
    // A disabled sessionStorage must not prevent an otherwise valid login.
  }
}

export function forgetXiaohongshuLogin(
  storage: SessionStorageLike | null = browserSessionStorage(),
) {
  if (!storage) return;
  try {
    storage.removeItem(XIAOHONGSHU_LOGIN_CACHE_KEY);
  } catch {
    // The backend remains the source of truth when browser storage is unavailable.
  }
}
