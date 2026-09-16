# HOLD — do not enable until Phase **2.5 green**

Per Ethan/Jarvis: keep these unit **templates** ready, but **do not** `systemctl enable` / install to `/etc/systemd/system` until Jarvis signals **2.5 green**.

When released:

```bash
sudo cp desk-jarvis-speak.service cloudflared-desk-jarvis.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now desk-jarvis-speak.service
sudo systemctl enable --now cloudflared-desk-jarvis.service
```

Named tunnel: edit `cloudflared-desk-jarvis.service` ExecStart to use `--config /opt/desk-jarvis/cloudflared/config.yml run` instead of quick tunnel.
