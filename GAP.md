# GAP.md - Permanent Differences from Picklebot

This document tracks features that exist in picklebot but will **never** be added to this tutorial project. These are intentional simplifications to keep the tutorial focused.

---

## Template Substitution

**Picklebot has:** `{{variable}}` placeholder substitution in AGENT.md and SKILL.md files

**Tutorial doesn't have:** Template substitution removed from code

**Files affected:**
- `default_workspace/BOOTSTRAP.md` - uses `{{workspace}}`, `{{skills_path}}`, etc.
- `default_workspace/skills/cron-ops/SKILL.md` - uses `{{crons_path}}`
- `default_workspace/agents/cookie/AGENT.md` - uses `{{memories_path}}`

**Why it's fine:**
- These files are from picklebot, included for reference
- Tutorial steps use simple skills that don't need path substitution
- Users learning from this tutorial should hard-code paths or use config values directly

---

## HTTP API Endpoints

**Picklebot has:**
- Full REST API with endpoints for skills/agents/crons/sessions/memories
- Complete API server with FastAPI routers

**Tutorial has:**
- WebSocket-only FastAPI server (no REST API endpoints)
- Just the `/ws` endpoint for real-time communication

**Why it's fine:**
- Tutorial focuses on real-time WebSocket communication
- REST API endpoints add complexity without teaching core concepts
- Users can add REST endpoints later if needed

---
