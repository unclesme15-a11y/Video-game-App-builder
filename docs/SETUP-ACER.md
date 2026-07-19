# Acer setup (Ubuntu server with GUI)

The Acer is the always-on brain: intelligence engine, builder agents, job
queue API. No GPU needed for any of it.

## 1. OS

- Install Ubuntu Desktop (the GUI costs ~1–1.5GB RAM vs Server — fine).
- Keep it running with the lid closed: edit `/etc/systemd/logind.conf`,
  set `HandleLidSwitch=ignore`, then `sudo systemctl restart systemd-logind`.
- Disable sleep: Settings → Power → Automatic Suspend → Off.
- Give it a static IP on your router (or note its LAN IP) so the Nitro can
  always find it.

## 2. Project

```bash
sudo apt install -y python3-venv git
git clone https://github.com/unclesme15-a11y/Video-game-App-builder.git
cd Video-game-App-builder
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # add your ANTHROPIC_API_KEY
```

## 3. Run the API (job queue + opportunity list)

```bash
uvicorn engine.api:app --host 0.0.0.0 --port 8000
```

To keep it running permanently, create `/etc/systemd/system/oie.service`:

```ini
[Unit]
Description=Opportunity Intelligence Engine
After=network.target

[Service]
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/Video-game-App-builder
ExecStart=/home/YOUR_USER/Video-game-App-builder/.venv/bin/uvicorn engine.api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then `sudo systemctl enable --now oie`.

## 4. Schedule intelligence passes

`crontab -e`:

```cron
0 */6 * * * cd /home/YOUR_USER/Video-game-App-builder && .venv/bin/python -m engine.pipeline >> pipeline.log 2>&1
```

## 5. Build something

```bash
python -m orchestrator.dispatcher
```

Picks the top opportunity scoring ≥ 8.2, writes a spec, and the builder agent
writes the project into `workspace/<project-name>/`. Unity builds get queued
for the Nitro automatically.
