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

var version = "latest"

func main() {
	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "ThreadPilot 启动失败：%v\n", err)
		fmt.Fprintln(os.Stderr, "请确认 Docker Desktop 已安装并正在运行。")
		if runtime.GOOS == "windows" {
			fmt.Fprintln(os.Stderr, "按回车键退出。")
			_, _ = fmt.Scanln()
		}
		os.Exit(1)
	}
}

func run() error {
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
	}

	args := []string{"compose", "-f", composePath, "--env-file", envPath}
	if len(os.Args) > 1 && os.Args[1] == "--stop" {
		return docker(root, append(args, "down"))
	}
	if len(os.Args) > 1 && os.Args[1] == "--open" {
		return openBrowser("http://localhost:3000/dashboard")
	}

	fmt.Println("正在启动 ThreadPilot，首次运行会下载容器镜像……")
	if err := docker(root, append(args, "up", "-d")); err != nil {
		return err
	}
	if err := waitFor("http://localhost:3000/dashboard", 3*time.Minute); err != nil {
		return err
	}
	fmt.Println("ThreadPilot 已就绪：http://localhost:3000/dashboard")
	return openBrowser("http://localhost:3000/dashboard")
}

func appDir() (string, error) {
	base, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(base, "ThreadPilot"), nil
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
	return strings.Join([]string{
		"APP_ENV=production",
		"APP_URL=http://localhost:3000",
		"SECRET_KEY=" + randomSecret(),
		"ENCRYPTION_KEY=" + randomSecret(),
		"POSTGRES_PASSWORD=" + randomSecret(),
		"LLM_PROVIDER=mock",
		"LLM_API_KEY=",
		"LLM_BASE_URL=https://api.openai.com/v1",
		"LLM_STRONG_MODEL=",
		"LLM_TIMEOUT_SECONDS=150",
		"LLM_ENABLE_THINKING=false",
		"GLOBAL_KILL_SWITCH=false",
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

func docker(dir string, args []string) error {
	cmd := exec.Command("docker", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), "THREADPILOT_VERSION="+version)
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
