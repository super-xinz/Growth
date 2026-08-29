# GrowthAgent Xiaohongshu MCP modifications

This image is built from `xpzouying/xiaohongshu-mcp` v2.5.0
(`6583124dfda92312b6bc19a042a6acfae63fe498`) under Apache-2.0.

GrowthAgent changes `xiaohongshu/login.go` to:

- use a non-blocking DOM probe while waiting for a QR login;
- recognize rotation of the authenticated `web_session` cookie;
- fall back to Xiaohongshu's semantic current-user state when the historical
  sidebar selector changes.

The source-form change is recorded in `login-session.patch`. GrowthAgent's
changes are also licensed under Apache-2.0.
