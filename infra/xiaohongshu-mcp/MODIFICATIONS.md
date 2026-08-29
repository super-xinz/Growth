# GrowthAgent Xiaohongshu MCP modifications

This image is built from `xpzouying/xiaohongshu-mcp` v2.5.0
(`6583124dfda92312b6bc19a042a6acfae63fe498`) under Apache-2.0.

GrowthAgent changes `xiaohongshu/login.go` to:

- detect and report Xiaohongshu login safety redirects instead of waiting until
  the API request is cancelled;
- bound QR-page navigation and selector waits, avoiding upstream `MustElement`
  panics and leaked headless-browser processes;
- use a non-blocking DOM probe while waiting for a QR login;
- recognize rotation of the authenticated `web_session` cookie;
- fall back to Xiaohongshu's semantic current-user state when the historical
  sidebar selector changes.

GrowthAgent also changes `service.go` so a QR browser is closed on every error
path and is transferred to the background scan waiter only after a valid QR
response is ready.

The source-form change is recorded in `login-session.patch`. GrowthAgent's
changes are also licensed under Apache-2.0.
