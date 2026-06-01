# Fantasy Hockey Draft Pick Tracker

Discord bot to keep track of and manage draft picks. Designed to replace the Fantrax paid version of trading future draft picks.

---

## Project structure

```
main.py                        — bot entry point
config.py                      — loads env variables
database/
  connection.py                — asyncpg pool + schema init
  queries.py                   — all SQL helpers
cogs/
  admin.py                     — /setup
  teams.py                     — /team add|rename|remove|list
  picks.py                     — /pick add|trade|remove|refresh
  season.py                    — /season_prep
fantasy-hockey-bot.service     — systemd unit for Linux
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- A Discord application with a bot token ([Discord Developer Portal](https://discord.com/developers/applications))

---

## Local setup

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd fantasy-hockey-draft-pick-tracker

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — fill in DISCORD_TOKEN and DATABASE_URL

# 5. Run
python main.py
```

---

## Linux server deployment (systemd)

```bash
# Copy files to server
sudo mkdir -p /opt/fantasy-hockey-bot
sudo cp -r . /opt/fantasy-hockey-bot

# Create a dedicated user
sudo useradd -r -s /bin/false discord

# Set up virtualenv on the server
cd /opt/fantasy-hockey-bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Create .env from the example
sudo cp .env.example .env
sudo nano .env   # fill in your values
sudo chown discord:discord .env
sudo chmod 600 .env

# Install and start the service
sudo cp fantasy-hockey-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fantasy-hockey-bot

# View logs
sudo journalctl -u fantasy-hockey-bot -f
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

The `/season_prep` command generates a separate embed listing every pick that changed hands, formatted as actionable steps for whoever administers the fantasy hockey website.
