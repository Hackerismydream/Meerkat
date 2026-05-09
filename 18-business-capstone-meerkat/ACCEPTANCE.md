# Meerkat v1 Acceptance

`make acceptance-v1` is the hard gate for claiming v1. It checks backend health,
Owncast health, webhook configuration, chat ingestion, stream probe lifecycle,
trace replay, dashboard summary, eval thresholds, and Owncast outbound dry-run.

Owncast being reachable is separate from the stream being online. The Owncast
page says offline until an RTMP source is pushing. On machines without local
`ffmpeg`, run:

```bash
make ffmpeg-stream-docker
```

Stop the test source with:

```bash
make ffmpeg-stream-stop
```

Simulation demos are deterministic local tests. They do not replace Owncast
acceptance.
