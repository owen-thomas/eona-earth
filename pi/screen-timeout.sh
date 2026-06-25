#!/bin/bash
# Screen timeout for eona clock — blanks HDMI after 1 hour of inactivity.
# Requires: swayidle, wlopm (apt install swayidle wlopm)
# Runs under the pi user's Wayland session via systemd user service.

TIMEOUT=3600

exec swayidle -w \
  timeout $TIMEOUT 'wlopm --off HDMI-A-1' \
  resume 'wlopm --on HDMI-A-1'
