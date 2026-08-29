export function safeOnboardingTarget(value: string | null | undefined) {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/account")) {
    return "/dashboard";
  }
  return value;
}

export function xiaohongshuOnboardingPath(pathname: string) {
  const target = safeOnboardingTarget(pathname);
  return `/account?onboarding=1&next=${encodeURIComponent(target)}`;
}
