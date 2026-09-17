# Phone POST /update

`POST https://desk.etjarvis.com/update` requires `ATLAS_SENDER_HEADER` (default `Authorization`) and `ATLAS_SENDER_KEY`. The handler pulls upstream, performs non-clobbering mapped sync, and schedules service restart after the response.
