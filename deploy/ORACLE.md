# Deploy on Oracle Cloud (Always Free)

## Step 1 — Create the VM

1. Log in to [Oracle Cloud Console](https://cloud.oracle.com/)
2. **☰ Menu → Compute → Instances → Create Instance**
3. Settings:
   - **Name:** `valorant-bot`
   - **Image:** Ubuntu 24.04 (or 22.04)
   - **Shape:** Click **Change Shape**
     - **Ampere** → **VM.Standard.A1.Flex**
     - Check **Always Free-eligible**
     - **2 OCPUs, 12 GB RAM** (or 1 OCPU / 6 GB if capacity is unavailable)
   - **Networking:** Use default VCN, assign **public IPv4**
   - **SSH keys:** Paste your public key (see below if you don't have one)
4. Click **Create**

### Generate SSH key (on your Mac, if needed)

```bash
ssh-keygen -t ed25519 -C "oracle-vps"
cat ~/.ssh/id_ed25519.pub
```

Copy the output and paste it when creating the instance.

5. Wait until the instance state is **Running**
6. Copy the **Public IP address**

---

## Step 2 — Open SSH port (if needed)

1. **Networking → Virtual Cloud Networks → your VCN → Security Lists → Default Security List**
2. Ensure an **Ingress Rule** exists:
   - Source: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port: **22**

---

## Step 3 — SSH into the server

```bash
ssh ubuntu@YOUR_PUBLIC_IP
```

---

## Step 4 — Install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git
```

---

## Step 5 — Clone vlrggapi

```bash
cd ~
git clone https://github.com/axsddlr/vlrggapi.git
cd vlrggapi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Test API
python main.py
```

Open another terminal on your Mac and test:

```bash
curl http://YOUR_PUBLIC_IP:3001/v2/health
```

Press `Ctrl+C` in the server terminal to stop the test (we'll use systemd next).

> **Note:** vlrggapi binds to localhost by default on many setups. The bot uses `127.0.0.1:3001` — do NOT expose port 3001 publicly.

---

## Step 6 — Upload your Discord bot

**Option A — SCP from your Mac:**

```bash
scp -r "/Users/ujjwal18/Desktop/discord bot " ubuntu@YOUR_PUBLIC_IP:~/discord-bot
```

**Option B — Git (if you pushed to GitHub):**

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/your-repo.git discord-bot
```

Then on the server:

```bash
cd ~/discord-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Set:

```env
DISCORD_TOKEN=your_real_token
VLR_API_BASE=http://127.0.0.1:3001
```

Save: `Ctrl+O`, Enter, `Ctrl+X`

---

## Step 7 — Enable systemd services (auto-start on boot)

```bash
sudo cp ~/discord-bot/deploy/vlrggapi.service /etc/systemd/system/
sudo cp ~/discord-bot/deploy/valorant-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vlrggapi valorant-bot
sudo systemctl start vlrggapi valorant-bot
```

Check status:

```bash
sudo systemctl status vlrggapi
sudo systemctl status valorant-bot
```

View logs:

```bash
journalctl -u vlrggapi -f
journalctl -u valorant-bot -f
```

---

## Step 8 — Firewall (recommended)

```bash
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw enable
```

Only SSH (port 22) should be open. The API stays on localhost.

---

## Step 9 — Verify in Discord

Your bot should show **Online**. Run in your server:

```
/status
/test-matches
```

---

## Useful commands

| Task | Command |
|------|---------|
| Restart bot | `sudo systemctl restart valorant-bot` |
| Restart API | `sudo systemctl restart vlrggapi` |
| View bot logs | `journalctl -u valorant-bot -n 50` |
| Edit .env | `nano ~/discord-bot/.env` then restart bot |

---

## Troubleshooting

**"Out of host capacity" when creating VM**
- Try a different home region, or retry later
- Use 1 OCPU / 6 GB instead of 2 / 12

**Bot offline**
- `journalctl -u valorant-bot -n 30` — check token errors

**API unhealthy in /status**
- `sudo systemctl status vlrggapi`
- `curl http://127.0.0.1:3001/v2/health` (run on the server)

**Can't SSH**
- Check Security List allows port 22
- Confirm you're using `ubuntu@PUBLIC_IP`
