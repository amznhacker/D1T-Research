# DDS Sanity Checklist

- Use `run_d1.sh` helper script to set UNITREE_NETWORK_INTERFACE
  - Script: `#!/usr/bin/env bash` + `export UNITREE_NETWORK_INTERFACE=enx4cea4168e514` + `exec "$@"`
  - Usage: `../../run_d1.sh ./command`
- Confirm correct NIC
- Expect silent wait on startup
- Telemetry confirms DDS health

