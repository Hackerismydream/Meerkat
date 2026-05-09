.PHONY: up down owncast-up owncast-logs owncast-down backend backend-setup check-owncast check-backend smoke-webhook ffmpeg-stream ffmpeg-no-audio probe-hls probe-ffprobe demo-owncast-message seed demo-pre-live-check demo-stream-down demo-stream-recover demo-no-audio demo-segment-stalled demo-coupon demo-inventory demo-price demo-price-risk demo-post-live-report eval test

PYTHON ?= $(CURDIR)/meerkat_backend/.venv/bin/python
BACKEND_URL ?= http://127.0.0.1:8018
OWNCAST_BASE_URL ?= http://127.0.0.1:8080
HLS_PLAYLIST_URL ?= $(OWNCAST_BASE_URL)/hls/stream.m3u8
STREAM_KEY ?= abc123

up: owncast-up

owncast-up:
	docker compose up -d owncast

owncast-logs:
	docker compose logs -f owncast

owncast-down:
	docker compose stop owncast && docker compose rm -f owncast

backend:
	cd meerkat_backend && $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8018 --reload

backend-setup: seed

check-owncast:
	OWNCAST_BASE_URL=$(OWNCAST_BASE_URL) $(PYTHON) scripts/check_owncast.py

check-backend:
	curl -fsS $(BACKEND_URL)/api/v1/health

smoke-webhook:
	curl -fsS -X POST $(BACKEND_URL)/api/v1/integrations/owncast/webhook -H 'Content-Type: application/json' -d '{"type":"CHAT","eventData":{"id":"smoke-1","body":"券领不了","user":{"displayName":"smoke","id":"smoke"}}}'

ffmpeg-stream:
	bash scripts/run_ffmpeg_test_stream.sh $(STREAM_KEY)

ffmpeg-no-audio:
	bash scripts/run_ffmpeg_no_audio_stream.sh $(STREAM_KEY)

probe-hls:
	curl -fsS $(HLS_PLAYLIST_URL) | head -20

probe-ffprobe:
	ffprobe -v error -show_streams $(HLS_PLAYLIST_URL)

demo-owncast-message:
	$(PYTHON) scripts/run_demo_owncast_message.py

seed:
	cd meerkat_backend && $(PYTHON) -m app.db.init_db --reset && $(PYTHON) -m app.db.seed

demo-coupon:
	$(PYTHON) scripts/run_demo_coupon.py

demo-pre-live-check:
	$(PYTHON) scripts/run_demo_pre_live_check.py

demo-inventory:
	$(PYTHON) scripts/run_demo_inventory.py

demo-price:
	$(PYTHON) scripts/run_demo_price.py

demo-price-risk:
	$(PYTHON) scripts/run_demo_price.py

demo-stream-down:
	$(PYTHON) scripts/run_demo_stream_down.py

demo-stream-recover:
	$(PYTHON) scripts/run_demo_stream_recover.py

demo-no-audio:
	$(PYTHON) scripts/run_demo_no_audio.py

demo-segment-stalled:
	$(PYTHON) scripts/run_demo_segment_stalled.py

demo-post-live-report:
	$(PYTHON) scripts/run_demo_post_live_report.py

eval:
	cd meerkat_agent/evals && $(PYTHON) run_eval.py

test:
	cd meerkat_backend && $(PYTHON) -m pytest -q

down:
	docker compose down
