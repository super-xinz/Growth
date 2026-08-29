package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func withManagedDefaults(t *testing.T, baseURL, model, token string) {
	t.Helper()
	oldBaseURL := managedLLMBaseURL
	oldModel := managedLLMModel
	oldToken := managedLLMGatewayToken
	managedLLMBaseURL = baseURL
	managedLLMModel = model
	managedLLMGatewayToken = token
	t.Cleanup(func() {
		managedLLMBaseURL = oldBaseURL
		managedLLMModel = oldModel
		managedLLMGatewayToken = oldToken
	})
}

func withVersion(t *testing.T, value string) {
	t.Helper()
	oldVersion := version
	version = value
	t.Cleanup(func() { version = oldVersion })
}

func TestDefaultEnvUsesManagedGatewayWithoutUpstreamKey(t *testing.T) {
	withManagedDefaults(
		t,
		"https://growthagent.example/api/v1/managed-llm",
		"deepseek-v4-flash",
		"release-gateway-token",
	)
	values := envValues(defaultEnv())
	if values["LLM_PROVIDER"] != "openai" || values["LLM_SETTINGS_LOCKED"] != "true" {
		t.Fatalf("managed LLM defaults were not enabled: %#v", values)
	}
	if values["LLM_API_KEY"] != "release-gateway-token" {
		t.Fatal("launcher did not use the revocable gateway token")
	}
	if !strings.HasPrefix(values["LLM_INSTALLATION_ID"], "ga_") {
		t.Fatal("launcher did not generate an installation id")
	}
}

func TestLauncherStartsWithXiaohongshuOnboarding(t *testing.T) {
	if onboardingURL != "http://localhost:3000/account?onboarding=1&next=%2Fdashboard" {
		t.Fatalf("unexpected onboarding URL: %s", onboardingURL)
	}
}

func TestDefaultEnvPinsPatchedXiaohongshuImageToRelease(t *testing.T) {
	withVersion(t, "v0.1.3")
	values := envValues(defaultEnv())
	if values["XIAOHONGSHU_MCP_IMAGE"] != "ghcr.io/super-xinz/growthagent-xiaohongshu:v0.1.3" {
		t.Fatalf("unexpected Xiaohongshu image: %q", values["XIAOHONGSHU_MCP_IMAGE"])
	}
}

func TestEnsureXiaohongshuImageEnvMigratesKnownUpstreamImage(t *testing.T) {
	withVersion(t, "v0.1.3")
	path := filepath.Join(t.TempDir(), ".env")
	original := "APP_ENV=production\nXIAOHONGSHU_MCP_IMAGE=xpzouying/xiaohongshu-mcp@sha256:old\n"
	if err := os.WriteFile(path, []byte(original), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := ensureXiaohongshuImageEnv(path); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	values := envValues(string(data))
	if values["XIAOHONGSHU_MCP_IMAGE"] != "ghcr.io/super-xinz/growthagent-xiaohongshu:v0.1.3" {
		t.Fatalf("upstream image was not migrated: %#v", values)
	}
}

func TestEnsureXiaohongshuImageEnvPreservesCustomImage(t *testing.T) {
	withVersion(t, "v0.1.3")
	path := filepath.Join(t.TempDir(), ".env")
	original := "XIAOHONGSHU_MCP_IMAGE=registry.example/custom-xhs:stable\n"
	if err := os.WriteFile(path, []byte(original), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := ensureXiaohongshuImageEnv(path); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != original {
		t.Fatal("launcher overwrote a custom Xiaohongshu image")
	}
}

func TestDefaultEnvFallsBackToMockWhenGatewayConfigIsIncomplete(t *testing.T) {
	withManagedDefaults(t, "https://growthagent.example/api/v1/managed-llm", "", "token")
	values := envValues(defaultEnv())
	if values["LLM_PROVIDER"] != "mock" || values["LLM_SETTINGS_LOCKED"] != "false" {
		t.Fatalf("incomplete gateway config must fail safe: %#v", values)
	}
}

func TestEnsureManagedLLMEnvUpgradesVirginMockConfig(t *testing.T) {
	withManagedDefaults(
		t,
		"https://growthagent.example/api/v1/managed-llm",
		"deepseek-v4-flash",
		"release-gateway-token",
	)
	path := filepath.Join(t.TempDir(), ".env")
	if err := os.WriteFile(path, []byte("LLM_PROVIDER=mock\nLLM_API_KEY=\nLLM_STRONG_MODEL=\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := ensureManagedLLMEnv(path); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	values := envValues(string(data))
	if values["LLM_PROVIDER"] != "openai" || values["LLM_STRONG_MODEL"] != "deepseek-v4-flash" {
		t.Fatalf("mock config was not upgraded: %#v", values)
	}
}

func TestEnsureManagedLLMEnvPreservesCustomProvider(t *testing.T) {
	withManagedDefaults(
		t,
		"https://growthagent.example/api/v1/managed-llm",
		"deepseek-v4-flash",
		"release-gateway-token",
	)
	path := filepath.Join(t.TempDir(), ".env")
	original := "LLM_PROVIDER=openai\nLLM_API_KEY=personal-key\nLLM_BASE_URL=https://custom.example/v1\nLLM_STRONG_MODEL=custom-model\nLLM_SETTINGS_LOCKED=false\n"
	if err := os.WriteFile(path, []byte(original), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := ensureManagedLLMEnv(path); err != nil {
		t.Fatal(err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != original {
		t.Fatal("launcher overwrote a user's custom model configuration")
	}
}
