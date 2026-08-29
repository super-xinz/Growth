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
