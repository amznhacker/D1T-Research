# Power-On Checklist — Unitree D1

1. Apply DC power
2. Wait 60–90 seconds
3. Verify:
   - ping 192.168.123.100
   - SSH availability
4. Do NOT rush DDS programs
5. Start SDK executables only after network stabilizes

## Troubleshooting

**If you see DDS exception: "does not match an available interface" or "Failed to create domain explicitly":**
- **First check: power cable connection**
- Error message is misleading; root cause is usually power disconnect
- See `bringup/2025-12-25_power_disconnect_error.md` for details



