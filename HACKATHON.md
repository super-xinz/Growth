# Guikesong submission record

## Submission links

- Source: <https://github.com/super-xinz/Growth>
- Live demo: <https://growthagent-guikesong.zeabur.app/>
- Release downloads: <https://github.com/super-xinz/Growth/releases>
- Submission tag: `#Guikesong`

## Scope and provenance

GrowthAgent entered the 2026-08-28 to 2026-08-29 development window with an existing local-first prototype, including the core product model, initial UI, and product screenshots. The work below is the contribution completed during the stated window; this repository does not represent the earlier prototype as newly created work.

## Work completed on 2026-08-28 to 2026-08-29

- Prepared separate API, Web, Worker, and Xiaohongshu MCP services for Zeabur deployment.
- Added a same-origin Next.js API proxy for hosted deployments.
- Made Alembic migrations repeatable on fresh and partially initialized databases.
- Removed an unused migration dependency and aligned migrations with the deployment database URL.
- Made Worker database sessions safe across repeated asynchronous event loops.
- Increased the Xiaohongshu status-check timeout for slower hosted environments.
- Added a public read-only boundary so the hosted demo cannot change settings, connect accounts, delete data, or publish content.
- Corrected repository, CI, Release, installation, and issue links for the public `Growth` repository.
- Added an explicit technology-stack table, downloadable launchers, CI fixes, and dependency-security updates.

## Verification

The submission is checked with:

```bash
pytest -q
ruff check apps/api tests
npm run lint --prefix apps/web
npm test --prefix apps/web
npm run typecheck --prefix apps/web
npm run build --prefix apps/web
go test ./...
docker compose config --quiet
docker compose -f compose.release.yml config --quiet
```

GitHub Actions repeats the same backend, frontend, launcher, Compose, and secret-scanning checks on every push to `main`.
