# HOLD — do not enable until Phase **2.5 green**

Per Ethan/Atlas: keep these unit **templates** ready, but **do not** `systemctl enable` / install to `/etc/systemd/system` until Atlas signals **2.5 green**.

When released:

```bash
sudo cp desk-atlas-speak.service cloudflared-desk-atlas.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now desk-atlas-speak.service
sudo systemctl enable --now cloudflared-desk-atlas.service
```

Named tunnel: edit `cloudflared-desk-atlas.service` ExecStart to use `--config /opt/desk-atlas/cloudflared/config.yml run` instead of quick tunnel.
