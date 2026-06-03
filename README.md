# Fantasy Hockey Draft Pick Tracker

Discord bot to keep track of and manage draft picks. Designed to replace the Fantrax paid version of trading future draft picks.

---

## Project structure

```
setup.py                       — one-time interactive setup (run first!)
main.py                        — bot entry point
config.py                      — reads bot_config.ini + decrypts token
bot_config.ini.example         — template for the plain-text config
webhook_server.py              — GitHub webhook listener (auto-pull on push to main)
database/
  credentials.py               — decrypts .db_creds.enc and builds the connection URL
  connection.py                — asyncpg pool + schema init
  queries.py                   — all SQL helpers
cogs/
  checks.py                    — shared admin-role permission check
  admin.py                     — /setup
  teams.py                     — /team add|rename|remove|list
  picks.py                     — /pick add|trade|remove|refresh
  season.py                    — /season_prep
fantasy-hockey-bot.service     — systemd unit for the bot
webhook.service                — systemd unit for the webhook server
```

### Files created by setup.py (never committed)

| File | Contents | Format |
|---|---|---|
| `bot_config.ini` | Guild ID, admin role, channel ID, webhook settings | Plain text — edit by hand to change |
| `.token.key` | Fernet encryption key (protects both encrypted files) | Binary, chmod 600 |
| `.token.enc` | Encrypted Discord bot token | Fernet ciphertext, chmod 600 |
| `.db_creds.enc` | Encrypted pickle: DB host, port, name, `FantasyBot` user + password | Encrypted pickle, chmod 600 |

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- A Discord application with a bot token ([Discord Developer Portal](https://discord.com/developers/applications))

---

## First-time setup (local or server)

```bash
# 1. Clone and enter the repo
git clone https://github.com/Enspist/fantasy-hockey-draft-pick-tracker.git
cd fantasy-hockey-draft-pick-tracker

# 2. Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run the setup wizard — this is the only setup step you need
python setup.py
#
#   PostgreSQL detection
#     • Scans localhost:5432 and :5433 automatically
#     • If not found locally, asks for remote IP + port
#     • Asks for DB name, master username, master password
#     • Creates the database and a 'FantasyBot' application user
#     • Saves encrypted credentials to .db_creds.enc
#
#   Discord
#     • Asks for bot token → encrypted in .token.enc (key in .token.key)
#
#   Bot settings  → bot_config.ini (plain text, editable by hand)
#     • Guild ID, admin role name, picks channel ID
#     • GitHub webhook secret + port

# 4. Start the bot
python main.py
```

To change **guild/role/channel settings** later, open `bot_config.ini` in any text editor.
To change the **Discord token**, run `python setup.py` again.

---

## Linux server deployment (systemd)

```bash
# Clone directly onto the server
sudo mkdir -p /opt/fantasy-hockey-bot
cd /opt/fantasy-hockey-bot
sudo git clone https://github.com/Enspist/fantasy-hockey-draft-pick-tracker.git .

# Create a dedicated low-privilege user
sudo useradd -r -s /bin/false discord
sudo chown -R discord:discord /opt/fantasy-hockey-bot

# Set up virtualenv
sudo -u discord python3 -m venv venv
sudo -u discord venv/bin/pip install -r requirements.txt

# Run the setup wizard as the service user
sudo -u discord venv/bin/python setup.py

# Install and start both services
sudo cp fantasy-hockey-bot.service /etc/systemd/system/
sudo cp webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fantasy-hockey-bot
sudo systemctl enable --now fantasy-hockey-bot-webhook

# View logs
sudo journalctl -u fantasy-hockey-bot -f
sudo journalctl -u fantasy-hockey-bot-webhook -f
```

---

## GitHub auto-pull (webhook server)

When you push to `main`, GitHub calls `http://<server>:<port>/webhook` and the
`webhook_server.py` process verifies the signature and runs `git pull origin main`.

**GitHub setup:**
1. Go to your repo → **Settings → Webhooks → Add webhook**
2. **Payload URL**: `http://<your-server-ip>:5000/webhook`
3. **Content type**: `application/json`
4. **Secret**: the `webhook_secret` you entered during `python setup.py`
5. **Events**: Just the push event

> **Note:** If your server is behind a firewall, open the webhook port (default 5000)
> for inbound connections, or use a reverse proxy (nginx) to forward a public HTTPS
> endpoint to the Flask server.

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

The `/season_prep` command generates a separate embed listing every pick that changed hands, formatted as actionable steps for whoever administers the fantasy hockey website.
