#!/usr/bin/env bash
# D1 Arm — Setup Script
# Configures network, patches SDK source with the correct NIC name, and builds.
# Run from the repo root on any Ubuntu machine.

set -uo pipefail

ROBOT_IP="192.168.123.100"
HOST_IP="192.168.123.10"
CON_NAME="d1-robot"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_SRC="$REPO_DIR/d1_sdk/src"
SDK_BUILD="$REPO_DIR/d1_sdk/build"

# ── Colours ──────────────────────────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[1;34m'
NC='\033[0m'

step()  { echo -e "\n${BLUE}${BOLD}==> $1${NC}"; }
ok()    { echo -e "  ${GREEN}✓${NC}  $1"; }
warn()  { echo -e "  ${YELLOW}!${NC}  $1"; }
err()   { echo -e "  ${RED}✗${NC}  $1"; }
die()   { err "$1"; exit 1; }

# ── 1. Dependencies ───────────────────────────────────────────────────────────
step "Checking dependencies"

for cmd in ip nmcli cmake make g++ ping; do
    if command -v "$cmd" &>/dev/null; then
        ok "$cmd"
    else
        case "$cmd" in
            g++)    die "g++ not found — run: sudo apt install build-essential" ;;
            cmake)  die "cmake not found — run: sudo apt install cmake" ;;
            nmcli)  die "nmcli not found — install NetworkManager: sudo apt install network-manager" ;;
            *)      die "$cmd not found" ;;
        esac
    fi
done

# Check unitree_sdk2 + CycloneDDS (required for build)
SDK2_HEADERS_OK=false
SDK2_LIBS_OK=false
ls /usr/local/include/ddscxx &>/dev/null && ls /usr/local/include/unitree &>/dev/null && SDK2_HEADERS_OK=true
ls /usr/local/lib/libunitree_sdk2.a &>/dev/null || ls /usr/local/lib/libunitree_sdk2.so &>/dev/null 2>/dev/null && SDK2_LIBS_OK=true

if $SDK2_HEADERS_OK && $SDK2_LIBS_OK; then
    ok "unitree_sdk2 + CycloneDDS found"
else
    err "unitree_sdk2 not installed."
    echo ""
    echo "  Install it with:"
    echo ""
    echo "    git clone https://github.com/unitreerobotics/unitree_sdk2"
    echo "    cd unitree_sdk2"
    echo "    mkdir build && cd build"
    echo "    cmake .."
    echo "    sudo make install"
    echo ""
    echo "  Then re-run this script."
    echo ""
    read -rp "  Continue anyway (build will fail)? [y/N] " CONT
    [[ "$CONT" =~ ^[Yy]$ ]] || exit 1
fi

# ── 2. Detect Ethernet interface ──────────────────────────────────────────────
step "Detecting Ethernet interface"

# Collect all non-loopback, non-wifi, non-virtual interfaces
ALL_IFACES=()
while IFS= read -r iface; do
    [[ "$iface" =~ ^(lo|wl|wlan|docker|virbr|veth|br-|bond|dummy|tun|tap) ]] && continue
    ALL_IFACES+=("$iface")
done < <(ip -o link show | awk -F': ' '{print $2}' | grep -v '@')

if [[ ${#ALL_IFACES[@]} -eq 0 ]]; then
    die "No Ethernet interfaces found. Plug in the cable and retry."
fi

# Among those, prefer ones with a carrier (cable actually plugged in)
WITH_CARRIER=()
for iface in "${ALL_IFACES[@]}"; do
    carrier=$(cat "/sys/class/net/$iface/carrier" 2>/dev/null || echo "0")
    [[ "$carrier" == "1" ]] && WITH_CARRIER+=("$iface")
done

if [[ ${#WITH_CARRIER[@]} -eq 1 ]]; then
    NIC="${WITH_CARRIER[0]}"
    ok "Auto-selected: $NIC (cable connected)"
elif [[ ${#WITH_CARRIER[@]} -gt 1 ]]; then
    warn "Multiple interfaces with a cable connected:"
    for i in "${!WITH_CARRIER[@]}"; do
        echo "    [$i] ${WITH_CARRIER[$i]}"
    done
    read -rp "  Enter the number for the robot interface: " IDX
    NIC="${WITH_CARRIER[$IDX]}"
    ok "Selected: $NIC"
elif [[ ${#ALL_IFACES[@]} -eq 1 ]]; then
    NIC="${ALL_IFACES[0]}"
    warn "No cable detected on $NIC — using it anyway. Plug in the cable now if needed."
else
    warn "No cable detected. Available interfaces:"
    for i in "${!ALL_IFACES[@]}"; do
        echo "    [$i] ${ALL_IFACES[$i]}"
    done
    read -rp "  Enter the number for the robot interface: " IDX
    NIC="${ALL_IFACES[$IDX]}"
    ok "Selected: $NIC"
fi

# ── 3. Check for IP collision ─────────────────────────────────────────────────
step "Checking for IP collision"

CURRENT_IP=$(ip -4 addr show "$NIC" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 || true)
if [[ "$CURRENT_IP" == "$ROBOT_IP" ]]; then
    warn "Host has robot IP ($ROBOT_IP) on $NIC — collision! Fixing now."
else
    [[ -n "$CURRENT_IP" ]] && ok "Current IP: $CURRENT_IP (no collision)" || ok "No IP assigned yet"
fi

# ── 4. Configure NetworkManager ───────────────────────────────────────────────
step "Configuring network ($NIC → $HOST_IP/24)"

# Remove every existing profile tied to this NIC
OLD_CONS=$(nmcli -t -f NAME,DEVICE connection show 2>/dev/null | grep ":$NIC" | cut -d: -f1 || true)
if [[ -n "$OLD_CONS" ]]; then
    while IFS= read -r con; do
        [[ -z "$con" ]] && continue
        nmcli connection delete "$con" &>/dev/null && warn "Removed old profile: $con"
    done <<< "$OLD_CONS"
fi

# Also remove by con-name in case it's orphaned
nmcli connection delete "$CON_NAME" &>/dev/null || true

# Create a clean persistent profile
nmcli connection add \
    type ethernet \
    ifname "$NIC" \
    con-name "$CON_NAME" \
    ipv4.method manual \
    ipv4.addresses "$HOST_IP/24" \
    ipv6.method ignore \
    connection.autoconnect yes &>/dev/null

nmcli connection up "$CON_NAME" &>/dev/null
ok "Profile '$CON_NAME' created and activated"

sleep 2  # give NetworkManager a moment to apply

# ── 5. Verify routing ─────────────────────────────────────────────────────────
step "Verifying routing"

ROUTE=$(ip route get "$ROBOT_IP" 2>/dev/null || true)
if echo "$ROUTE" | grep -q "dev $NIC" && echo "$ROUTE" | grep -q "src $HOST_IP"; then
    ok "ip route get $ROBOT_IP → dev $NIC src $HOST_IP"
else
    warn "Unexpected route: $ROUTE"
    warn "If commands don't work, reconnect the cable and re-run this script."
fi

# ── 6. Ping test ──────────────────────────────────────────────────────────────
step "Testing connectivity to robot ($ROBOT_IP)"

if ping -c 2 -W 2 -I "$NIC" "$ROBOT_IP" &>/dev/null; then
    ok "ping $ROBOT_IP — robot is up"
    ARP=$(ip neigh show dev "$NIC" 2>/dev/null | grep "$ROBOT_IP" || true)
    [[ -n "$ARP" ]] && ok "ARP: $ARP"
else
    warn "ping failed — robot may be off or still booting"
    warn "Power on the robot, wait 60–90 s, then run: ping $ROBOT_IP"
fi

# ── 7. Patch SDK source files ─────────────────────────────────────────────────
step "Patching SDK source files with interface: $NIC"

PATCHED=0
for f in "$SDK_SRC"/*.cpp; do
    [[ -f "$f" ]] || continue
    if grep -q 'ChannelFactory::Instance()->Init' "$f"; then
        # Replace Init(0) or Init(0, "anything") → Init(0, "<NIC>")
        sed -i "s|ChannelFactory::Instance()->Init(0[^)]*)|ChannelFactory::Instance()->Init(0, \"$NIC\")|g" "$f"
        ok "$(basename "$f")"
        PATCHED=$((PATCHED + 1))
    fi
done

[[ $PATCHED -eq 0 ]] && warn "No Init() calls found to patch — check $SDK_SRC"

# ── 8. Build ──────────────────────────────────────────────────────────────────
step "Building SDK (clean build)"

rm -rf "$SDK_BUILD"
mkdir -p "$SDK_BUILD"
cd "$SDK_BUILD"

if ! cmake .. -DCMAKE_BUILD_TYPE=Release &>/tmp/d1_cmake.log 2>&1; then
    err "cmake failed. Full output:"
    cat /tmp/d1_cmake.log
    die "Fix dependencies and re-run."
fi

if ! make -j"$(nproc)" &>/tmp/d1_make.log 2>&1; then
    err "make failed. Full output:"
    cat /tmp/d1_make.log
    die "Fix build errors and re-run."
fi

BINS=(arm_zero_control get_arm_joint_angle joint_angle_control joint_enable_control multiple_joint_angle_control)
BUILD_OK=true
for b in "${BINS[@]}"; do
    if [[ -f "$SDK_BUILD/$b" ]]; then
        ok "$b"
    else
        err "$b — not found after build"
        BUILD_OK=false
    fi
done

$BUILD_OK || die "Some binaries are missing. Check /tmp/d1_make.log"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}=== Setup complete ===${NC}"
echo ""
echo -e "  Interface  : ${BOLD}$NIC${NC}"
echo -e "  Host IP    : ${BOLD}$HOST_IP${NC}"
echo -e "  Robot IP   : ${BOLD}$ROBOT_IP${NC}"
echo -e "  Binaries   : ${BOLD}$SDK_BUILD/${NC}"
echo ""
echo "  Power on the robot, wait 60–90 s, then:"
echo ""
echo "    cd $SDK_BUILD"
echo "    ./get_arm_joint_angle          # verify telemetry (10 Hz stream)"
echo "    ./joint_enable_control         # lock joints"
echo "    ./arm_zero_control             # move to zero"
echo ""
echo "  See d1_guide.ipynb for full reference."
echo ""
