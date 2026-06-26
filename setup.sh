#!/usr/bin/env bash
# D1 Arm — Setup Script
# Configures network, patches SDK source with the correct NIC name, and builds.
# Run from the repo root on any Ubuntu machine. Safe to re-run.

set -uo pipefail

ROBOT_IP="192.168.123.100"
HOST_IP="192.168.123.10"
CON_NAME="d1-robot"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_SRC="$REPO_DIR/d1_sdk/src"
SDK_BUILD="$REPO_DIR/d1_sdk/build"
SDK_LOG_DIR="$REPO_DIR/d1_sdk"

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

# nmcli wrapper: tries without sudo first, falls back to sudo
nmcli_run() {
    nmcli "$@" &>/dev/null && return 0
    warn "nmcli requires elevated privileges — retrying with sudo"
    sudo nmcli "$@" &>/dev/null
}

# ── 1. System packages ────────────────────────────────────────────────────────
step "Checking / installing system packages"

APT_PKGS=()
command -v g++    &>/dev/null || APT_PKGS+=(build-essential)
command -v cmake  &>/dev/null || APT_PKGS+=(cmake)
command -v git    &>/dev/null || APT_PKGS+=(git)
command -v nmcli  &>/dev/null || APT_PKGS+=(network-manager)
command -v ping   &>/dev/null || APT_PKGS+=(iputils-ping)

if [[ ${#APT_PKGS[@]} -gt 0 ]]; then
    warn "Installing missing packages: ${APT_PKGS[*]}"
    sudo apt-get install -y "${APT_PKGS[@]}" || die "apt-get install failed"
fi

for cmd in ip nmcli cmake make g++ ping git; do
    command -v "$cmd" &>/dev/null && ok "$cmd" || die "$cmd still missing after install attempt"
done

# ── 2. unitree_sdk2 + CycloneDDS ─────────────────────────────────────────────
step "Checking unitree_sdk2 + CycloneDDS"

SDK2_HEADERS_OK=false
SDK2_LIBS_OK=false
{ ls /usr/local/include/ddscxx &>/dev/null && ls /usr/local/include/unitree &>/dev/null; } && SDK2_HEADERS_OK=true
{ ls /usr/local/lib/libunitree_sdk2.a &>/dev/null || ls /usr/local/lib/libunitree_sdk2.so &>/dev/null; } 2>/dev/null && SDK2_LIBS_OK=true

if $SDK2_HEADERS_OK && $SDK2_LIBS_OK; then
    ok "unitree_sdk2 + CycloneDDS already installed"
else
    warn "unitree_sdk2 not found — cloning and installing (this takes a few minutes)"
    SDK2_TMP=$(mktemp -d)
    trap 'rm -rf "$SDK2_TMP"' EXIT

    git clone --depth 1 https://github.com/unitreerobotics/unitree_sdk2 "$SDK2_TMP/unitree_sdk2" \
        || die "git clone of unitree_sdk2 failed — check your internet connection"

    cmake -S "$SDK2_TMP/unitree_sdk2" -B "$SDK2_TMP/unitree_sdk2/build" \
        || die "cmake configure of unitree_sdk2 failed"

    sudo make -C "$SDK2_TMP/unitree_sdk2/build" -j"$(nproc)" install \
        || die "make install of unitree_sdk2 failed"

    rm -rf "$SDK2_TMP"
    trap - EXIT
    ok "unitree_sdk2 installed"
fi

# Regenerate linker cache so libddsc.so.0 is found at runtime
sudo ldconfig && ok "ldconfig updated"

# ── 3. Detect Ethernet interface ──────────────────────────────────────────────
step "Detecting Ethernet interface"

ALL_IFACES=()
while IFS= read -r iface; do
    # Exclude loopback, wifi, virtual, and bridge interfaces
    [[ "$iface" =~ ^(lo|wl|wlan|docker|virbr|veth|br-|br[0-9]|bond|dummy|tun|tap) ]] && continue
    ALL_IFACES+=("$iface")
done < <(ip -o link show | awk -F': ' '{print $2}' | grep -v '@')

if [[ ${#ALL_IFACES[@]} -eq 0 ]]; then
    die "No Ethernet interfaces found. Plug in the cable and retry."
fi

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

# ── 4. Check for IP collision ─────────────────────────────────────────────────
step "Checking for IP collision"

CURRENT_IP=$(ip -4 addr show "$NIC" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1 || true)
if [[ "$CURRENT_IP" == "$ROBOT_IP" ]]; then
    warn "Host has robot IP ($ROBOT_IP) on $NIC — collision! Fixing now."
else
    [[ -n "$CURRENT_IP" ]] && ok "Current IP: $CURRENT_IP (no collision)" || ok "No IP assigned yet"
fi

# ── 5. Configure NetworkManager ───────────────────────────────────────────────
step "Configuring network ($NIC → $HOST_IP/24)"

OLD_CONS=$(nmcli -t -f NAME,DEVICE connection show 2>/dev/null | grep ":$NIC" | cut -d: -f1 || true)
if [[ -n "$OLD_CONS" ]]; then
    while IFS= read -r con; do
        [[ -z "$con" ]] && continue
        nmcli_run connection delete "$con" && warn "Removed old profile: $con"
    done <<< "$OLD_CONS"
fi

nmcli_run connection delete "$CON_NAME" || true

nmcli_run connection add \
    type ethernet \
    ifname "$NIC" \
    con-name "$CON_NAME" \
    ipv4.method manual \
    ipv4.addresses "$HOST_IP/24" \
    ipv6.method ignore \
    connection.autoconnect yes \
    || die "nmcli connection add failed"

nmcli_run connection up "$CON_NAME" \
    || die "nmcli connection up failed"

ok "Profile '$CON_NAME' created and activated"

sleep 2

# ── 6. Verify routing ─────────────────────────────────────────────────────────
step "Verifying routing"

ROUTE=$(ip route get "$ROBOT_IP" 2>/dev/null || true)
if echo "$ROUTE" | grep -q "dev $NIC" && echo "$ROUTE" | grep -q "src $HOST_IP"; then
    ok "ip route get $ROBOT_IP → dev $NIC src $HOST_IP"
else
    warn "Unexpected route: $ROUTE"
    warn "If commands don't work, reconnect the cable and re-run this script."
fi

# ── 7. Ping test ──────────────────────────────────────────────────────────────
step "Testing connectivity to robot ($ROBOT_IP)"

if ping -c 2 -W 2 -I "$NIC" "$ROBOT_IP" &>/dev/null; then
    ok "ping $ROBOT_IP — robot is up"
    ARP=$(ip neigh show dev "$NIC" 2>/dev/null | grep "$ROBOT_IP" || true)
    [[ -n "$ARP" ]] && ok "ARP: $ARP"
else
    warn "ping failed — robot may be off or still booting"
    warn "Power on the robot, wait 60–90 s, then run: ping $ROBOT_IP"
fi

# ── 8. Patch SDK source files ─────────────────────────────────────────────────
step "Patching SDK source files with interface: $NIC"

PATCHED=0
NIC_CHANGED=false
for f in "$SDK_SRC"/*.cpp; do
    [[ -f "$f" ]] || continue
    if grep -q 'ChannelFactory::Instance()->Init' "$f"; then
        CURRENT=$(grep -o 'Init(0, "[^"]*"' "$f" | grep -o '"[^"]*"' | tr -d '"' | head -1 || true)
        if [[ "$CURRENT" != "$NIC" ]]; then
            sed -i "s|ChannelFactory::Instance()->Init(0[^)]*)|ChannelFactory::Instance()->Init(0, \"$NIC\")|g" "$f"
            ok "$(basename "$f")  ($CURRENT → $NIC)"
            NIC_CHANGED=true
        else
            ok "$(basename "$f")  (already $NIC)"
        fi
        PATCHED=$((PATCHED + 1))
    fi
done

[[ $PATCHED -eq 0 ]] && warn "No Init() calls found to patch — check $SDK_SRC"

# ── 9. Build (skip if up-to-date) ────────────────────────────────────────────
step "Building SDK"

BINS=(arm_zero_control get_arm_joint_angle joint_angle_control joint_enable_control multiple_joint_angle_control)
NEEDS_BUILD=false

# Missing binaries?
for b in "${BINS[@]}"; do
    if [[ ! -f "$SDK_BUILD/$b" ]]; then
        NEEDS_BUILD=true
        warn "Binary missing: $b"
        break
    fi
done

# Source newer than any binary?
if ! $NEEDS_BUILD; then
    while IFS= read -r src; do
        for b in "${BINS[@]}"; do
            if [[ "$SDK_BUILD/$b" -ot "$src" ]]; then
                NEEDS_BUILD=true
                warn "Source changed: $(basename "$src") — rebuilding"
                break 2
            fi
        done
    done < <(find "$SDK_SRC" -name '*.cpp')
fi

if ! $NEEDS_BUILD; then
    ok "Binaries are up-to-date — skipping build"
else
    cd "$REPO_DIR"
    rm -rf "$SDK_BUILD"
    mkdir -p "$SDK_BUILD"

    if ! cmake -S "$REPO_DIR/d1_sdk" -B "$SDK_BUILD" -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_BUILD_RPATH=/usr/local/lib \
            >"$SDK_LOG_DIR/cmake.log" 2>&1; then
        err "cmake failed. Full output:"
        cat "$SDK_LOG_DIR/cmake.log"
        die "Fix dependencies and re-run."
    fi

    if ! make -C "$SDK_BUILD" -j"$(nproc)" >"$SDK_LOG_DIR/make.log" 2>&1; then
        err "make failed. Full output:"
        cat "$SDK_LOG_DIR/make.log"
        die "Fix build errors and re-run."
    fi
fi

BUILD_OK=true
for b in "${BINS[@]}"; do
    if [[ -f "$SDK_BUILD/$b" ]]; then
        ok "$b"
    else
        err "$b — not found after build"
        BUILD_OK=false
    fi
done

$BUILD_OK || die "Some binaries are missing. Check $SDK_LOG_DIR/make.log"

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
