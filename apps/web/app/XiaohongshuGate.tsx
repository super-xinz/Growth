"use client";

import {useEffect, useState} from "react";
import {usePathname, useRouter} from "next/navigation";
import {API, responseDetail} from "@/lib/api";
import {xiaohongshuOnboardingPath} from "@/lib/onboarding";

type GateState = "checking" | "ready" | "redirecting" | "unavailable";

export default function XiaohongshuGate({publicDemo}: {publicDemo: boolean}) {
  const pathname = usePathname();
  const router = useRouter();
  const [state, setState] = useState<GateState>(
    publicDemo || pathname === "/account" ? "ready" : "checking",
  );
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (publicDemo || pathname === "/account") {
      setState("ready");
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20_000);
    setState("checking");
    setError("");

    void (async () => {
      try {
        const response = await fetch(`${API}/v1/xiaohongshu/status`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(await responseDetail(response));
        const status = await response.json();
        if (status.is_logged_in) {
          setState("ready");
          return;
        }
        setState("redirecting");
        router.replace(xiaohongshuOnboardingPath(pathname));
      } catch (reason) {
        if (controller.signal.aborted) {
          setError("小红书服务仍在启动，请稍后重试。");
        } else {
          setError(reason instanceof Error ? reason.message : "无法检查小红书登录状态");
        }
        setState("unavailable");
      } finally {
        window.clearTimeout(timeout);
      }
    })();

    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [attempt, pathname, publicDemo, router]);

  if (state === "ready") return null;

  return <div className="login-gate" role={state === "unavailable" ? "alert" : "status"}>
    <section className="login-gate-card">
      <div className="eyebrow">首次使用</div>
      <h1>{state === "unavailable" ? "暂时无法连接小红书" : "正在确认小红书登录"}</h1>
      <p>{state === "unavailable" ? error : "模型和运行参数已自动配置，只需完成小红书扫码登录。"}</p>
      {state === "unavailable"
        ? <button className="button" onClick={() => setAttempt(value => value + 1)}>重新检查</button>
        : <span className="spinner" aria-hidden="true"/>}
    </section>
  </div>;
}
