# Meerkat Architecture

Meerkat is split into three explicit roles:

- Owncast provides livestream infrastructure: RTMP, web playback, chat, webhook events, and optional integration messages.
- Meerkat Backend owns business state: rooms, sessions, products, aliases, inventory, coupons, scripts, comments, clusters, stream samples, incidents, alerts, notes, approvals, reports, and agent logs.
- Meerkat Agent owns diagnosis and action selection: commander dispatches sub-agents, tools read/write backend state, risk guard blocks sensitive actions, and trace logs explain every step.

```text
Owncast CHAT / STREAM events
  + simulation comments
  + stream health samples
        |
        v
Meerkat Backend
  live_rooms / live_sessions / products / coupons / inventory
  comments / comment_clusters / stream_health_samples / stream_incidents
  ops_alerts / speaker_notes / approval_tasks / post_live_reports
        |
        v
AgentTask -> commander
  stream_monitor / live_triage / product / coupon / policy / risk / script / report
        |
        v
ToolRegistry -> RiskGuard -> trace -> backend writes
```

The backend may create candidates, but final business actions should be produced by agent tools. That boundary keeps the project agent-first: alerts, speaker notes, approvals, reports, and trace evidence are outcomes of the workflow, not hidden side effects of a classifier.
