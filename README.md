# Luraph Deobfuscator – web (Vercel)

## 1. Get the Linux luau binaries (required, one time)
The engine needs a **patched** Luau (`luau` + `luau-ast`); the .exe files in the original zip don't run on Linux.
- Push this folder to GitHub → **Actions → build-luau → Run workflow**. It builds and commits `engine/bin/luau` and `engine/bin/luau-ast`.
- (Or locally on Linux: `cd engine && python3 build_luau.py --portable`, then commit `engine/bin/*`.)

## 2. Deploy
1. Import the GitHub repo in Vercel (Framework: Other). No build command needed.
2. Env vars: `DEOBF_TIMEOUT` = `270` (Pro / Fluid) or `50` (Hobby, 60s limit).
3. Deploy → open the URL.

## Long jobs / bigger scripts
Heavy scripts can take minutes. Run the same code on a Docker host (Railway, Fly.io, Render, VPS):
`docker build -t deobf . && docker run -p 8080:8080 deobf`
then in Vercel set `BACKEND_URL=https://your-backend` and the Vercel site just forwards to it.
