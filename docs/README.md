# Skein — GitHub Pages Website

A polished, responsive static website for **Skein — The Continuous Thread of AI-DLC**.

## Included

- Large branded Skein logo in the hero
- Light, brand-enhancing visual system
- Cyan / electric blue / violet / magenta / coral / orange / mint palette
- Responsive navigation with mobile menu
- Hero status bar
- Why Skein section
- Capability cards
- AI-DLC Control Plane lifecycle
- Quick-start tabs with copy interaction
- Architecture visualization
- Ecosystem positioning
- Governance principles
- GitHub CTAs
- Scroll progress indicator
- Reveal-on-scroll animation
- Reduced-motion support
- No framework, build step, or external runtime dependency

## Files

```text
.
├── index.html
├── styles.css
├── script.js
├── README.md
└── assets/
    ├── skein-logo.png
    ├── skein-mark.png
```

## GitHub Pages

1. Copy the contents of this folder to your website repository.
2. Commit and push to GitHub.
3. In **Settings → Pages**, select the branch/folder containing `index.html`.
4. Open the generated Pages URL.

## Local preview

Because this is a static site, any simple HTTP server works:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## Design direction

The visual system intentionally uses a light canvas so the Skein logo becomes the focal point. Brand colors are used as controlled accents rather than flooding the page:

- Deep Navy `#07112F`
- Cyan `#00B8F2`
- Electric Blue `#2867F0`
- Violet `#7436E8`
- Magenta `#D63FC4`
- Coral `#FF6B5B`
- Orange `#F58A3A`
- Mint `#00C2A8`

The page is intentionally dependency-free so it can be hosted directly from GitHub Pages.
