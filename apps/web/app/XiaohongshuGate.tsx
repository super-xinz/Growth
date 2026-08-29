"use client";

import {useEffect, useState} from "react";
import {usePathname, useRouter} from "next/navigation";
import {API, responseDetail} from "@/lib/api";
import {xiaohongshuOnboardingPath} from "@/lib/onboarding";
import {
  forgetXiaohongshuLogin,
  readXiaohongshuLoginConfirmation,
  rememberXiaohongshuLogin,
} from "@/lib/xiaohongshu-session";

type GateState = "checking" | "ready" | "redirecting" | "unavailable";

let pendingStatusCheck: Promise<boolean> | null = null;

function checkXiaohongshuStatus() {
  if (pendingStatusCheck) return pendingStatusCheck;

  pendingStatusCheck = (async () => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    try {
      const response = await fetch(`${API}/v1/xiaohongshu/status`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(await responseDetail(response));
      const status = await response.json();
      return Boolean(status.is_logged_in);
    } finally {
      window.clearTimeout(timeout);
    }
  })().finally(() => {
    pendingStatusCheck = null;
  });

  return pendingStatusCheck;
}

export default function XiaohongshuGate({enabled}: {enabled: boolean}) {
  const pathname = usePathname();
  const router = useRouter();
  const [state, setState] = useState<GateState>("ready");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!enabled || pathname === "/account" || pathname === "/access") {
      setState("ready");
      return;
    }

    let cancelled = false;
    const confirmation = readXiaohongshuLoginConfirmation();
    if (confirmation?.fresh) {
      setState("ready");
      return;
    }

    // A previously confirmed session may continue while its slow browser-based
    // status check runs in the background. Only a brand-new session is blocked.
    setState(confirmation ? "ready" : "checking");
    setError("");

    void (async () => {
      try {
        const isLoggedIn = await checkXiaohongshuStatus();
        if (cancelled) return;
        if (isLoggedIn) {
          rememberXiaohongshuLogin();
          setState("ready");
          return;
        }
        forgetXiaohongshuLogin();
        setState("redirecting");
        router.replace(xiaohongshuOnboardingPath(pathname));
      } catch (reason) {
        if (cancelled) return;
        if (confirmation) {
          setState("ready");
          return;
        }
        if (reason instanceof DOMException && reason.name === "AbortError") {
          setError("小红书服务仍在启动，请稍后重试。");
        } else {
          setError(reason instanceof Error ? reason.message : "无法检查小红书登录状态");
        }
        setState("unavailable");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [attempt, enabled, pathname, router]);

  if (state === "ready") return null;

  return <div className="login-gate" role={state === "unavailable" ? "alert" : "status"}>
    <section className="login-gate-card">
      <div className="eyebrow">账号连接</div>
      <h1>{state === "unavailable" ? "暂时无法连接小红书" : "正在确认小红书登录"}</h1>
      <p>{state === "unavailable" ? error : "模型和运行参数已自动配置，只需完成小红书扫码登录。"}</p>
      {state === "unavailable"
        ? <button className="button" onClick={() => setAttempt(value => value + 1)}>重新检查</button>
        : <span className="spinner" aria-hidden="true"/>}
    </section>
  </div>;
}
