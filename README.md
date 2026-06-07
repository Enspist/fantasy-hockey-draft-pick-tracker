# Fantasy Draft Pick Tracker

Discord bot to keep track of and manage fantasy-sports draft picks. Works for any fantasy league (hockey, football, basketball, baseball, etc.). Designed to replace the Fantrax paid version of trading future draft picks.

---

## Project structure

```
install.py / install.sh / install.cmd  — first-time installer (run once)
run.py     / run.sh     / run.cmd      — start the bot
setup.py                               — interactive config wizard (called by installer)
main.py                                — Discord bot entry point (pulls latest on startup)
paths.py                               — central definitions for all config/secret file paths
config.py                              — reads config/bot_config.yaml + decrypts secrets
config/
  bot_config.yaml.example      — template for the YAML config
  secret/                      — hidden folder holding the encrypted .pkl secrets
database/
  credentials.py               — decrypts config/secret/db_creds.pkl and builds the connection URL
  connection.py                — asyncpg pool + schema init
  queries.py                   — all SQL helpers
cogs/
  checks.py                    — shared admin-role permission checks
  admin.py                     — /setup
  management.py                — /bot restart
  settings.py                  — /rounds, /years
  teams.py                     — /team add|rename|remove|list
  picks.py                     — /pick add|trade|remove|refresh
  season.py                    — /season_prep
fantasy-draft-bot.service      — systemd unit for Linux (alternative to run.sh)
```

### Files created by setup.py (never committed — all live in `config/`)

| File | Contents | Format |
|---|---|---|
| `config/bot_config.yaml` | Guild ID, admin role, optional bot-manager role, channel ID, log_keep | YAML — edit by hand to change |
| `config/secret/token_key.pkl` | Fernet encryption key (protects both secrets) | Pickled bytes, hidden, chmod 600 |
| `config/secret/token.pkl` | Encrypted Discord bot token | Pickled ciphertext, hidden, chmod 600 |
| `config/secret/db_creds.pkl` | Encrypted DB host, port, name, `FantasyBot` user + password | Pickled ciphertext, hidden, chmod 600 |

---

## How updates work

Every time the bot starts it runs `git pull` before connecting to Discord, so it is always on the latest code. Because the repo was cloned over HTTPS without credentials, pushing is not possible — anyone running the bot can only pull. All commits must come from an authorised GitHub account. (Set `NO_PULL=1` to skip the pull when testing local changes.)

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- A Discord application with a bot token ([Discord Developer Portal](https://discord.com/developers/applications))

---

## First-time setup (local or server)

Clone the repo, then run the installer once. It handles everything — venv creation, dependency install, and the interactive config wizard.

**Linux / macOS**
```bash
git clone https://github.com/Enspist/fantasy-hockey-draft-pick-tracker.git
cd fantasy-hockey-draft-pick-tracker
bash install.sh
```

**Windows**
```
Double-click install.cmd
— or —
python install.py
```

**Any platform (Python directly)**
```bash
python install.py
```

The installer will:
- Create `./venv` and install all dependencies
- Auto-detect PostgreSQL on `localhost:5432` / `:5433` (asks for remote host/port if not found)
- Prompt for DB name, master username, master password → creates the DB + `FantasyBot` app user
- Prompt for Discord bot token → encrypted in `config/secret/token.pkl` / `config/secret/token_key.pkl`
- Prompt for guild ID, admin role, optional bot-manager role, channel ID → saved to `config/bot_config.yaml`

To change **guild/role/channel settings** later, open `config/bot_config.yaml` in any text editor.
To update the **Discord token** or **DB credentials**, run `python setup.py` again.

---

## Starting the bot

**Linux / macOS**
```bash
bash run.sh
```

**Windows**
```
Double-click run.cmd
— or —
python run.py
```

**Any platform**
```bash
python run.py
```

On startup the bot pulls the latest code from `main`, then connects to Discord.
Press `Ctrl+C` to stop.

---

## Linux server deployment (systemd)

For a full step-by-step guide (installing PostgreSQL, an LXC container, running
as a background service that survives terminal close), see **[DEPLOY.md](DEPLOY.md)**.

Quick version:

```bash
git clone https://github.com/Enspist/fantasy-hockey-draft-pick-tracker.git
cd fantasy-hockey-draft-pick-tracker
bash install.sh

# Install and start the service
sudo cp fantasy-draft-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fantasy-draft-bot

# View logs
sudo journalctl -u fantasy-draft-bot -f
```

---

## First-time bot configuration

1. Invite the bot to your server with `applications.commands` and `bot` scopes.
2. Run `/setup channel:#your-channel` to designate the pick board channel.
3. Add teams with `/team add name:Team Name`.
4. Add each team's picks with `/pick add team:Team Name year:2026 round:1`.
5. Record trades with `/pick trade original_team:A year:2026 round:1 new_owner:B`.

---

## Slash command reference

| Command | Permission | Description |
|---|---|---|
| `/setup channel` | Admin | Set the channel for the pick board embed |
| `/team add name` | Admin | Add a new team |
| `/team rename old_name new_name` | Admin | Rename a team (saved to DB) |
| `/team remove name` | Admin | Delete a team and all its picks |
| `/team list` | Everyone | List all teams |
| `/pick add team year round` | Admin | Add a pick to a team's original holdings |
| `/pick trade original_team year round new_owner` | Admin | Transfer a pick to another team |
| `/pick remove original_team year round` | Admin | Delete a pick record |
| `/pick refresh` | Everyone | Re-post the pick board |
| `/season_prep year` | Admin | Post the pre-season pick transfer checklist |

---

## How the pick board works

After any change the bot automatically edits the last board embed it posted in the configured channel (or posts a new one). Each team's field lists every pick it currently holds, with a note showing the original team if the pick was traded.

The `/season_prep` command generates a separate embed listing every pick that changed hands, formatted as actionable steps for whoever administers the fantasy league website.
