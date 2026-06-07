# Deployment Guide — Ubuntu (LXC container or VM)

This guide installs PostgreSQL and the bot on a fresh Ubuntu system, then runs
the bot as a **systemd service** so it:

- keeps running after you close the terminal / SSH session, and
- leaves your command line free for other work.

The commands are identical across recent Ubuntu releases (22.04, 24.04, 26.04).

---

## 1. Update the system & install prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql postgresql-contrib python3 python3-venv python3-pip git
```

## 2. Start PostgreSQL

```bash
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
```

## 3. Set a password on the master `postgres` user

The bot's `setup.py` connects as the master user to create its own database and
a dedicated `FantasyBot` user. Give the `postgres` role a password:

```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'choose_a_strong_master_password';"
```

> Remember this password — `setup.py` asks for it during installation.

## 4. Clone the bot and create a service user

```bash
sudo git clone https://github.com/Enspist/fantasy-hockey-draft-pick-tracker.git /opt/fantasy-draft-bot
sudo useradd -r -s /bin/false discord
sudo chown -R discord:discord /opt/fantasy-draft-bot
```

## 5. Run the installer as the service user

Creates the virtual environment, installs dependencies, and runs the interactive
setup wizard:

```bash
cd /opt/fantasy-draft-bot
sudo -u discord bash install.sh
```

The wizard will:

- Auto-detect PostgreSQL on `localhost:5432`
- Ask for the database name (default `fantasy_draft`), master username
  (`postgres`), and the master password from step 3
- Create the database and the `FantasyBot` application user automatically
- Ask for your Discord bot token (shown so you can verify it, then encrypted)
- Ask for the guild ID, admin role, optional bot-manager role, and picks channel ID

## 6. Install and start the systemd service

This is what detaches the bot from your terminal:

```bash
sudo cp /opt/fantasy-draft-bot/fantasy-draft-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fantasy-draft-bot
```

- `enable` → starts automatically on boot
- `--now` → starts it immediately
- Because it runs under systemd, you can close the terminal/SSH session and the
  bot keeps running, with your command line free.

## 7. Manage and monitor

```bash
sudo systemctl status fantasy-draft-bot      # is it running?
sudo journalctl -u fantasy-draft-bot -f      # live logs (Ctrl+C stops watching, not the bot)
sudo systemctl restart fantasy-draft-bot     # restart
sudo systemctl stop fantasy-draft-bot        # stop
```

---

## LXC container notes

**systemd must run inside the container.** Standard Ubuntu LXC/LXD containers run
systemd as PID 1 by default, so this works out of the box. Verify with:

```bash
systemctl is-system-running    # "running" or "degraded" is fine; an error is not
```

If it errors with *"Failed to connect to bus,"* the container was created without
systemd — recreate it from a standard `ubuntu:24.04` (or newer) image rather than a
minimal/`busybox` base.

---

## Updating the bot

The bot runs `git pull` on startup, so it self-updates from `main` whenever it
restarts. To update on demand:

```bash
sudo systemctl restart fantasy-draft-bot
```

The in-Discord `/bot restart` command also pulls the latest code and re-launches
the process — systemd keeps the service alive through the re-exec.

---

## Changing configuration later

- **Settings** (guild ID, roles, channel, log_keep): edit
  `/opt/fantasy-draft-bot/config/bot_config.yaml`, then restart the service.
- **Discord token or database credentials**: re-run the setup wizard:
  ```bash
  cd /opt/fantasy-draft-bot
  sudo -u discord venv/bin/python setup.py
  sudo systemctl restart fantasy-draft-bot
  ```
