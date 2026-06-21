#!/bin/bash

# ==============================================
# Скрипт для включения режима точки доступа Wi‑Fi
# на Raspberry Pi 4 с Ubuntu 25.10
# (сохраняет статический IP через systemd-networkd)
# ==============================================

# ---------- Настройки (можно менять) ----------
AP_SSID="Copter239"
AP_PASSWORD="copter239"
AP_IP="10.239.239.239"
AP_CHANNEL=7
WLAN_IFACE="wlan0"
# ----------------------------------------------

if [[ $EUID -ne 0 ]]; then
    echo "Запустите скрипт с правами root: sudo bash $0"
    exit 1
fi

echo ">>> Настройка точки доступа Wi-Fi <<<"
echo "SSID: $AP_SSID, пароль: $AP_PASSWORD, IP: $AP_IP"

# --- 1. Установка необходимых пакетов ---
echo ">>> Установка пакетов..."
apt update || true
apt install -y hostapd dnsmasq iw rfkill iptables-persistent netfilter-persistent || true

# --- 2. Остановка конфликтующих сервисов ---
echo ">>> Остановка мешающих служб..."
systemctl stop NetworkManager 2>/dev/null || true
systemctl disable NetworkManager 2>/dev/null || true
systemctl mask NetworkManager 2>/dev/null || true

systemctl stop wpa_supplicant 2>/dev/null || true
systemctl disable wpa_supplicant 2>/dev/null || true
systemctl mask wpa_supplicant 2>/dev/null || true

systemctl stop systemd-resolved 2>/dev/null || true
systemctl disable systemd-resolved 2>/dev/null || true
systemctl mask systemd-resolved 2>/dev/null || true

# --- 3. Включаем systemd-networkd (снимаем маски) и настраиваем только wlan0 ---
echo ">>> Настройка systemd-networkd для $WLAN_IFACE..."
# Убираем маски, если были
systemctl unmask systemd-networkd.service 2>/dev/null || true
systemctl unmask systemd-networkd.socket 2>/dev/null || true

# Создаём конфиг для статического IP на wlan0
cat > /etc/systemd/network/10-wlan0.network << EOF
[Match]
Name=$WLAN_IFACE

[Network]
Address=$AP_IP/24
IPForward=yes
# Отключаем DHCP-клиент на wlan0
DHCP=no
EOF

# Удаляем другие конфиги, которые могут мешать
rm -f /etc/systemd/network/20-enx.network

# Перезапускаем systemd-networkd
systemctl enable systemd-networkd
systemctl restart systemd-networkd

# --- 4. Явно задаём IP сейчас (чтобы не ждать перезагрузки) ---
ip link set $WLAN_IFACE down
iw dev $WLAN_IFACE set type ap 2>/dev/null || true
ip addr flush dev $WLAN_IFACE
ip addr add $AP_IP/24 dev $WLAN_IFACE
ip link set $WLAN_IFACE up

# --- 5. Конфигурация hostapd ---
echo ">>> Настройка hostapd..."
cat > /etc/hostapd/hostapd.conf << EOF
interface=$WLAN_IFACE
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=$AP_CHANNEL
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

sed -i 's|^#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

# --- 6. Конфигурация dnsmasq (DHCP) ---
echo ">>> Настройка dnsmasq..."
mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak 2>/dev/null || true
cat > /etc/dnsmasq.conf << EOF
interface=$WLAN_IFACE
dhcp-range=10.239.239.100,10.239.239.200,255.255.255.0,24h
dhcp-option=3,$AP_IP
dhcp-option=6,8.8.8.8,8.8.4.4
no-resolv
server=8.8.8.8
EOF

# --- 7. Включение IP-форвардинга ---
echo ">>> Включение IP-маршрутизации..."
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-ipforward.conf
sysctl -p /etc/sysctl.d/99-ipforward.conf || true

# --- 8. Настройка NAT (автовыбор внешнего интерфейса) ---
echo ">>> Настройка правил iptables..."
EXT_IFACE=""
for iface in $(ls /sys/class/net/); do
    if [[ "$iface" =~ ^enx[0-9a-f]+ ]] || [[ "$iface" == "eth0" ]]; then
        if ip link show "$iface" | grep -q "state UP" && ip addr show "$iface" | grep -q "inet "; then
            EXT_IFACE="$iface"
            break
        fi
    fi
done
if [[ -z "$EXT_IFACE" ]]; then
    EXT_IFACE="eth0"
    echo "⚠ Внешний интерфейс не найден. Использую $EXT_IFACE (проверьте вручную)."
else
    echo "✓ Внешний интерфейс: $EXT_IFACE"
fi

iptables -t nat -F POSTROUTING
iptables -F FORWARD
iptables -t nat -A POSTROUTING -o $EXT_IFACE -j MASQUERADE
iptables -A FORWARD -i $WLAN_IFACE -o $EXT_IFACE -j ACCEPT
iptables -A FORWARD -i $EXT_IFACE -o $WLAN_IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT

netfilter-persistent save || true

# --- 9. Удаляем старый кастомный сервис (он больше не нужен) ---
echo ">>> Удаление старого wlan0-ap-mode.service (если был)..."
systemctl stop wlan0-ap-mode.service 2>/dev/null || true
systemctl disable wlan0-ap-mode.service 2>/dev/null || true
rm -f /etc/systemd/system/wlan0-ap-mode.service
systemctl daemon-reload

# --- 10. Запуск точки доступа ---
echo ">>> Запуск hostapd и dnsmasq..."
systemctl unmask hostapd 2>/dev/null || true
systemctl enable hostapd
systemctl start hostapd || { echo "Ошибка запуска hostapd. Проверьте статус."; exit 1; }

systemctl enable dnsmasq
systemctl start dnsmasq || { echo "Ошибка запуска dnsmasq. Проверьте статус."; exit 1; }

# --- 11. Финальная проверка ---
echo ""
echo "==========================================="
echo "Точка доступа '$AP_SSID' успешно запущена!"
echo "IP-адрес Raspberry Pi: $AP_IP"
echo "Пароль Wi-Fi: $AP_PASSWORD"
echo ""
echo "Проверка статуса:"
echo "  systemctl status hostapd"
echo "  systemctl status dnsmasq"
echo "  networkctl status wlan0"
echo ""
echo "После перезагрузки все настройки сохранятся."
echo "==========================================="
