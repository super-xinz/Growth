package main

import (
	"crypto/rand"
	"embed"
	"encoding/base64"
	"errors"
	"fmt"
	"io/fs"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

//go:embed all:assets
var bundled embed.FS

var (
	version                = "latest"
	managedLLMBaseURL      = ""
	managedLLMModel        = ""
	managedLLMGatewayToken = ""
)

const onboardingURL = "http://localhost:3000/account?onboarding=1&next=%2Fdashboard"

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "GrowthAgent 启动失败：%v\n", err)
		fmt.Fprintln(os.Stderr, "请确认 Docker Desktop 已安装并正在运行。")
		if runtime.GOOS == "windows" {
			fmt.Fprintln(os.Stderr, "按回车键退出。")
			_, _ = fmt.Scanln()
		}
		os.Exit(1)
	}
}

func run() error {
	if len(os.Args) > 1 && os.Args[1] == "--version" {
		fmt.Printf("GrowthAgent %s\n", version)
		return nil
	}
	if _, err := exec.LookPath("docker"); err != nil {
		return errors.New("没有找到 Docker，请先安装 Docker Desktop")
	}
	root, err := appDir()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(root, 0o700); err != nil {
		return err
	}
	composePath := filepath.Join(root, "compose.yml")
	if err := writeBundled("assets/compose.yml", composePath); err != nil {
		return err
	}
	envPath := filepath.Join(root, ".env")
	if _, err := os.Stat(envPath); errors.Is(err, os.ErrNotExist) {
		if err := os.WriteFile(envPath, []byte(defaultEnv()), 0o600); err != nil {
			return err
		}
	} else if err != nil {
		return err
	} else {
		if err := ensureManagedLLMEnv(envPath); err != nil {
			return err
		}
		if err := ensureXiaohongshuImageEnv(envPath); err != nil {
			return err
		}
	}

	args := []string{"compose", "-f", composePath, "--env-file", envPath}
	if len(os.Args) > 1 && os.Args[1] == "--stop" {
		return docker(root, append(args, "down"))
	}
	if len(os.Args) > 1 && os.Args[1] == "--open" {
		return openBrowser(onboardingURL)
	}

	fmt.Println("正在启动 GrowthAgent，首次运行会下载容器镜像……")
	if err := docker(root, append(args, "up", "-d")); err != nil {
		return err
	}
	if err := waitFor("http://localhost:3000/dashboard", 3*time.Minute); err != nil {
		return err
	}
	fmt.Println("GrowthAgent 已就绪，请在浏览器中扫码登录小红书。")
	return openBrowser(onboardingURL)
}

func appDir() (string, error) {
	base, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	root := filepath.Join(base, "GrowthAgent")
	legacyRoot := filepath.Join(base, "ThreadPilot")
	if _, err := os.Stat(root); errors.Is(err, os.ErrNotExist) {
		if _, legacyErr := os.Stat(legacyRoot); legacyErr == nil {
			return legacyRoot, nil
		}
	}
	return root, nil
}

func writeBundled(name, target string) error {
	data, err := fs.ReadFile(bundled, name)
	if err != nil {
		return err
	}
	return os.WriteFile(target, data, 0o600)
}

func randomSecret() string {
	data := make([]byte, 32)
	if _, err := rand.Read(data); err != nil {
		panic(err)
	}
	return base64.RawURLEncoding.EncodeToString(data)
}

func defaultEnv() string {
	provider := "mock"
	apiKey := ""
	baseURL := "https://api.deepseek.com"
	model := ""
	locked := "false"
	if managedLLMConfigured() {
		provider = "openai"
		apiKey = managedLLMGatewayToken
		baseURL = managedLLMBaseURL
		model = managedLLMModel
		locked = "true"
	}
	return strings.Join([]string{
		"APP_ENV=production",
		"APP_URL=http://localhost:3000",
		"SECRET_KEY=" + randomSecret(),
		"ENCRYPTION_KEY=" + randomSecret(),
		"POSTGRES_PASSWORD=" + randomSecret(),
		"LLM_PROVIDER=" + provider,
		"LLM_API_KEY=" + apiKey,
		"LLM_BASE_URL=" + baseURL,
		"LLM_STRONG_MODEL=" + model,
		"LLM_TIMEOUT_SECONDS=150",
		"LLM_ENABLE_THINKING=false",
		"LLM_SETTINGS_LOCKED=" + locked,
		"LLM_DISPLAY_NAME=\"GrowthAgent AI\"",
		"LLM_INSTALLATION_ID=ga_" + randomSecret(),
		"GLOBAL_KILL_SWITCH=false",
		"XIAOHONGSHU_MCP_IMAGE=" + xiaohongshuImage(),
		"XHS_PROXY=",
		"XIAOHONGSHU_SEARCH_TIMEOUT_SECONDS=75",
		"XIAOHONGSHU_AUTO_SCORE_THRESHOLD=0.75",
		"XIAOHONGSHU_AUTO_RISK_THRESHOLD=0.35",
		"XIAOHONGSHU_SEARCH_INTERVAL_HOURS=3",
		"XIAOHONGSHU_MIN_PUBLISH_INTERVAL_HOURS=4",
		"XIAOHONGSHU_KEYWORDS_PER_RUN=3",
		"XIAOHONGSHU_DETAILS_PER_KEYWORD=2",
		"",
	}, "\n")
}

func xiaohongshuImage() string {
	tag := strings.TrimSpace(version)
	if tag == "" {
		tag = "latest"
	}
	return "ghcr.io/super-xinz/growthagent-xiaohongshu:" + tag
}

func ensureXiaohongshuImageEnv(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	content := string(data)
	current := strings.TrimSpace(envValues(content)["XIAOHONGSHU_MCP_IMAGE"])
	if current != "" && !strings.HasPrefix(current, "xpzouying/xiaohongshu-mcp") {
		return nil
	}

	replacement := "XIAOHONGSHU_MCP_IMAGE=" + xiaohongshuImage()
	lines := strings.Split(strings.TrimSuffix(content, "\n"), "\n")
	replaced := false
	for index, line := range lines {
		if strings.HasPrefix(line, "XIAOHONGSHU_MCP_IMAGE=") {
			lines[index] = replacement
			replaced = true
			break
		}
	}
	if !replaced {
		lines = append(lines, replacement)
	}
	return os.WriteFile(path, []byte(strings.Join(lines, "\n")+"\n"), 0o600)
}

func managedLLMConfigured() bool {
	values := []string{managedLLMBaseURL, managedLLMModel, managedLLMGatewayToken}
	for _, value := range values {
		if strings.TrimSpace(value) == "" || strings.ContainsAny(value, "\r\n") {
			return false
		}
	}
	return strings.HasPrefix(managedLLMBaseURL, "https://")
}

func ensureManagedLLMEnv(path string) error {
	if !managedLLMConfigured() {
		return nil
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	content := string(data)
	values := envValues(content)
	locked := strings.EqualFold(values["LLM_SETTINGS_LOCKED"], "true")
	provider := strings.TrimSpace(values["LLM_PROVIDER"])
	customProvider := provider != "" && provider != "mock" && !locked
	if customProvider {
		return nil
	}

	installationID := values["LLM_INSTALLATION_ID"]
	if !strings.HasPrefix(installationID, "ga_") {
		installationID = "ga_" + randomSecret()
	}
	updates := map[string]string{
		"LLM_PROVIDER":        "openai",
		"LLM_API_KEY":         managedLLMGatewayToken,
		"LLM_BASE_URL":        managedLLMBaseURL,
		"LLM_STRONG_MODEL":    managedLLMModel,
		"LLM_SETTINGS_LOCKED": "true",
		"LLM_DISPLAY_NAME":    "\"GrowthAgent AI\"",
		"LLM_INSTALLATION_ID": installationID,
	}
	order := []string{
		"LLM_PROVIDER",
		"LLM_API_KEY",
		"LLM_BASE_URL",
		"LLM_STRONG_MODEL",
		"LLM_SETTINGS_LOCKED",
		"LLM_DISPLAY_NAME",
		"LLM_INSTALLATION_ID",
	}
	lines := strings.Split(strings.TrimSuffix(content, "\n"), "\n")
	seen := make(map[string]bool, len(updates))
	for index, line := range lines {
		key, _, found := strings.Cut(line, "=")
		if !found {
			continue
		}
		if value, ok := updates[key]; ok {
			lines[index] = key + "=" + value
			seen[key] = true
		}
	}
	for _, key := range order {
		if !seen[key] {
			lines = append(lines, key+"="+updates[key])
		}
	}
	return os.WriteFile(path, []byte(strings.Join(lines, "\n")+"\n"), 0o600)
}

func envValues(content string) map[string]string {
	values := make(map[string]string)
	for _, line := range strings.Split(content, "\n") {
		key, value, found := strings.Cut(line, "=")
		if found && key != "" && !strings.HasPrefix(key, "#") {
			values[key] = value
		}
	}
	return values
}

func docker(dir string, args []string) error {
	cmd := exec.Command("docker", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), "GROWTHAGENT_VERSION="+version)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func waitFor(url string, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	client := &http.Client{Timeout: 3 * time.Second}
	for time.Now().Before(deadline) {
		response, err := client.Get(url)
		if err == nil {
			_ = response.Body.Close()
			if response.StatusCode >= 200 && response.StatusCode < 500 {
				return nil
			}
		}
		time.Sleep(2 * time.Second)
	}
	return errors.New("服务启动超时，请运行 docker compose logs 查看原因")
}

func openBrowser(url string) error {
	var command *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		command = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		command = exec.Command("open", url)
	default:
		command = exec.Command("xdg-open", url)
	}
	return command.Start()
}
