# Studio Agent — Roadmap

## Current State (PoC)

Working proof of concept:
- Opens Ableton Live
- Loads stems into Session view via AbletonOSC
- Copies each track to Arrangement view via AppleScript
- Mac only, Ableton only, sequential

**Not production ready.** No error recovery, no retries, non-deterministic.

---

## Target Architecture — Python Pipeline

A clean, deterministic pipeline. One LLM call to parse intent. The rest is Python.

```
instruction (natural language)
   ↓
[email_parser]         — LLM: parse intent, find email, classify attachments
   ↓
[downloader]      — Python: parallel downloads, file validation
   ↓
[preflight]     — Python: environment checks, DAW ready state
   ↓
[loader]          — Python: load stems, verify each track
   ↓
[verifier]        — Python: reconcile expected vs actual DAW state
   ↓
report
```

Most of the pipeline is deterministic Python. The LLM sits at the entry point to interpret the instruction and extract structured intent. No LLM overhead in the hot path.

---

## Pipeline Definitions

### email_parser
**Responsibility:** Parse the instruction, locate the relevant email, classify each file by source type.

**LLM:** Yes — intent parsing, email identification from natural language

**Outputs:** Structured stem list — filename, source type (attachment / Drive / WeTransfer), download metadata

**Failure modes:**
- No email found → fail hard
- No audio files in email → fail hard
- Mixed source types → route each to correct handler

---

### downloader
**Responsibility:** Download all stems in parallel. Validate each file is genuine audio.

**LLM:** No — pure Python

**Outputs:** Verified local file paths, normalised filenames

**Failure modes:**
- Direct attachment → Gmail API `attachments.get`
- Google Drive link → Drive API
- WeTransfer / Dropbox → page scrape for direct URL
- Corrupt / invalid file → retry up to 3x, skip and report if still failing
- Partial success → continue with valid files, surface failures in final report

---

### preflight
**Responsibility:** Prepare the environment. Block until DAW is ready.

**LLM:** No — pure Python

**Steps:**
1. Kill stale port processes
2. Validate files on disk
3. Open DAW
4. Poll for OSC readiness (timeout: 30s)
5. Confirm DAW browser can see all files

**Failure modes:**
- DAW timeout → fail hard
- Files not visible in browser → fail hard
- Port conflict → kill and retry

---

### loader
**Responsibility:** Load each stem. Verify each one before moving to the next.

**LLM:** No — pure Python

**Steps (per track):**
1. Create audio track
2. Drain OSC receive port
3. Load file to session slot
4. Verify OSC success response
5. Copy to Arrangement
6. Verify clip count incremented

**Failure modes:**
- Load fails → retry once with extended delay
- Silent AppleScript fail → verify clip count, retry
- Clip missing after retry → partial failure, continue

---

### verifier
**Responsibility:** Final reconciliation. Expected vs actual DAW state.

**LLM:** No — pure Python

**Outputs:** Full success or structured failure report listing missing tracks

---

## Milestones

### Milestone 1 — Hardened Ableton Flow
- [ ] Refactor current script into discrete, testable functions
- [ ] OSC response verification per track
- [ ] Retry logic for AppleScript copy step
- [ ] Preflight as a single validated function
- **Goal:** Zero silent failures.

### Milestone 2 — Python Pipeline
- [ ] Wire all functions into a clean pipeline
- [ ] Single LLM call at entry point (parse instruction → structured intent)
- [ ] End-to-end test with stems pre-downloaded
- **Goal:** Deterministic, one-command flow.

### Milestone 3 — Email Pipeline
- [ ] email_parser — Gmail API, attachment classification
- [ ] downloader — parallel downloads, Drive API, file validation
- [ ] Full pipeline: email → download → preflight → load → verify
- **Goal:** One message, full pipeline.

### Milestone 4 — DAW Agnostic
- [ ] Reaper adapter (OSC + ReaScript)
- [ ] Windows support (UI Automation replaces AppleScript)
- [ ] Logic Pro adapter
- **Goal:** Any DAW, any OS.
