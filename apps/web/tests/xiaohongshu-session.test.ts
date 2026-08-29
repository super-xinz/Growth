import assert from "node:assert/strict";
import test from "node:test";
import {
  forgetXiaohongshuLogin,
  readXiaohongshuLoginConfirmation,
  rememberXiaohongshuLogin,
  type SessionStorageLike,
  XIAOHONGSHU_LOGIN_RECHECK_MS,
} from "../lib/xiaohongshu-session.ts";

function createStorage(): SessionStorageLike {
  const values = new Map<string, string>();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

test("remembers a confirmed Xiaohongshu login for the browser session", () => {
  const storage = createStorage();
  rememberXiaohongshuLogin(storage, 10_000);

  assert.deepEqual(readXiaohongshuLoginConfirmation(storage, 20_000), {
    confirmedAt: 10_000,
    fresh: true,
  });
});

test("keeps an old confirmation but marks it for silent revalidation", () => {
  const storage = createStorage();
  rememberXiaohongshuLogin(storage, 10_000);

  assert.deepEqual(
    readXiaohongshuLoginConfirmation(
      storage,
      10_000 + XIAOHONGSHU_LOGIN_RECHECK_MS,
    ),
    {confirmedAt: 10_000, fresh: false},
  );
});

test("forgets the browser confirmation after logout", () => {
  const storage = createStorage();
  rememberXiaohongshuLogin(storage, 10_000);
  forgetXiaohongshuLogin(storage);

  assert.equal(readXiaohongshuLoginConfirmation(storage, 20_000), null);
});

test("ignores invalid or future confirmation values", () => {
  const invalidStorage = createStorage();
  invalidStorage.setItem("growthagent:xiaohongshu-login-confirmed-at", "not-a-time");
  assert.equal(readXiaohongshuLoginConfirmation(invalidStorage, 20_000), null);

  const futureStorage = createStorage();
  rememberXiaohongshuLogin(futureStorage, 100_001);
  assert.equal(readXiaohongshuLoginConfirmation(futureStorage, 20_000), null);
});
