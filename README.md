# Studio Agent

> Control any DAW with a single message.

Studio Agent is a DAW-agnostic AI agent workflow. Send a natural language command — load stems, set tempo, create tracks — and the agent handles the rest, regardless of which DAW you use.

## The Problem

Every DAW has a different workflow. Loading stems means opening Ableton, finding files, dragging them in, naming tracks. It's setup tax. Every time. Before you've played a single note.

## The Vision

```
"Load the stems from my email into the arrangement"
```

That's it. One message. The agent reads your email, downloads the files, opens your DAW, creates tracks, loads every stem. By the time you sit down at your laptop, everything is ready.

## DAW Support

| DAW | Status | Protocol |
|-----|--------|----------|
| Ableton Live | ✅ Working | AbletonOSC |
| Reaper | 🔜 Next | OSC + ReaScript |
| Logic Pro | 🔜 Planned | AppleScript |
| FL Studio | 🔜 Planned | FL Studio API |

## Architecture

```
┌─────────────────────────────────┐
│         Natural Language        │
│   "load stems into ableton"     │
└────────────────┬────────────────┘
                 │
┌────────────────▼────────────────┐
│         Studio Agent            │
│   LangGraph agent workflow      │
│                                 │
│  email → download → preflight   │
│       → load → verify           │
└────────────────┬────────────────┘
                 │
    ┌────────────▼────────────┐
    │     DAW Adapter Layer    │
    └──┬──────────┬───────────┘
       │          │
  ┌────▼───┐  ┌───▼────┐
  │Ableton │  │ Reaper │  ...
  └────────┘  └────────┘
```

## Getting Started

```bash
git clone https://github.com/Dandiggas/studio-agent
cd studio-agent
pip install -r requirements.txt
```

Requires AbletonOSC installed in your Ableton Remote Scripts folder.

## Roadmap

See [ROADMAP.md](ROADMAP.md)

## Background

Built by [Dan Diggas](https://github.com/Dandiggas) — 15 years as a professional music producer, backend engineer. This project sits at the intersection of both worlds.

## License

MIT
