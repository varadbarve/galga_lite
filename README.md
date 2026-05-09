# Galga Lite

A lightweight Galga-style obstacle dodging game built with Python + Pygame.

## Features

- Player spaceship with smooth left/right movement
- Procedural incoming obstacles
- Progressive phases with increasing obstacle speed and density
- Start screen and restart flow
- Score based on survival time

## Run Locally (Desktop)

```powershell
cd galga_lite
python -m pip install -r requirements.txt
python main.py
```

## Build for Web (Pygbag)

```powershell
cd galga_lite
python -m pip install -r requirements.txt
python -m pygbag --build .
```

After build, Pygbag generates `build/web`.

## Prepare Vercel Static Folder

Copy built files into `web-dist`:

```powershell
cd galga_lite
Remove-Item -Recurse -Force web-dist -ErrorAction SilentlyContinue
Copy-Item -Recurse build\web web-dist
```

## Deploy to Vercel

```powershell
cd galga_lite
npx vercel --prod
```

`vercel.json` routes all traffic to `web-dist`.

## Controls

- Move left: `Left Arrow` or `A`
- Move right: `Right Arrow` or `D`
- Start: `Space` or `Enter`
- Restart after game over: `R` or `Enter`
- Exit: `Esc`
