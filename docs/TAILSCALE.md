# Desk Atlas — Tailscale (Tesla Guest / away LAN)

## What this fixes

**Tesla Guest Wi‑Fi isolates clients.** Your phone/Mac and the Pi can both reach the internet, but they often **cannot talk to each other on the LAN**. That breaks home-style SSH (`orangepi@192.168.x.x`).

**Tailscale** puts the Pi, Mac, and phone on a private mesh (`100.x` addresses). Then you can SSH/admin the Pi from work even when Guest blocks LAN peers.

## What does *not* need Tailscale

Day-to-day voice already uses:

- **On-device** wake / ears / local time-date
- **Outbound HTTPS** webhook → Atlas
- **Named tunnel mouth** `https://desk.etjarvis.com` → speak

That path worked on Guest without Tailscale. Use Tailscale for **SSH, file copy, and rare debug** — not for every spoken reply.

## One-time setup (Ethan)

### 1. Account

1. Create/login at [https://login.tailscale.com](https://login.tailscale.com) (same Google/Apple you use for other Ethan gear is fine).
2. On a machine that is already signed in, open **Settings → Keys** and create a **reusable auth key** *only if* you want headless Pi join. Prefer interactive login on the Pi the first time at home.

### 2. Install on the Orange Pi (home LAN once)

SSH as usual, then:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Browser/URL login when prompted. Confirm:

```bash
tailscale status
tailscale ip -4
```

Save the `100.x.y.z` address somewhere you can find it (Notes / Atlas). Hostname is often `orangepizero2w`.

Optional — start on boot (usually already enabled by the package):

```bash
sudo systemctl enable --now tailscaled
```

### 3. Mac + iPhone

- Mac: install Tailscale from App Store or [tailscale.com/download](https://tailscale.com/download), sign in, turn on.
- iPhone: Tailscale app, same account, turn on when at Tesla Guest.

### 4. SSH from work

With Tailscale up on both ends:

```bash
ssh orangepi@100.x.y.z
# or
ssh orangepi@orangepizero2w
```

MagicDNS may resolve the hostname if enabled in the Tailscale admin console.

## Guest Wi‑Fi quirks

- If direct WireGuard UDP is blocked, Tailscale falls back to **DERP relay**. SSH still works; it may feel slower. Fine for `/update` debug and rare fixes.
- Keep **phone Tailscale on** while you need Pi admin. Day-to-day desk use can leave phone Tailscale off if you only need voice + tunnel.

## Optional health check (on the Pi)

Repo script (after sync/pull):

```bash
bash ~/desk-atlas-upstream/software/ops/check-tailscale.sh
# or from live tree if copied:
bash ~/desk-atlas/check-tailscale.sh
```

Exit `0` = `tailscaled` active + has an IPv4. Exit non‑zero = print a short hint (not a hard failure for desk-atlas.service — voice must keep working without Tailscale).

Optional systemd oneshot (disabled by default — enable only if you want a boot log line):

```bash
# after files are on the Pi
sudo cp ~/desk-atlas-upstream/software/ops/tailscale-check.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tailscale-check.service   # optional
```

## Security

- Never commit Tailscale auth keys, `.env`, or API keys.
- Prefer ACLs in the Tailscale admin console if you add more devices later.
- Tailscale does **not** replace speak/update auth on `desk.etjarvis.com`.

## Related

- Mouth / tunnel: `docs/TUNNEL.md`
- Phone OTA: `git-sync/UPDATE-PHONE.md`
