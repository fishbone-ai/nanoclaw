# Fishbone US VPN Setup

WireGuard VPN server in Azure (West US 2) for browsing US Google Shopping results as a US user.

**Server IP:** `20.69.100.77`
**WireGuard port:** `51820/udp`

## Prerequisites

macOS: Install WireGuard from the App Store or via Homebrew:

```bash
brew install wireguard-tools
```

## Step 1: Generate your keys

```bash
wg genkey | tee ~/wg-private.key | wg pubkey > ~/wg-public.key
chmod 600 ~/wg-private.key
```

Send the contents of `~/wg-public.key` to Avishay. He'll register your peer and assign you an IP (e.g. `10.10.0.X`).

## Step 2: Create your client config

Once Avishay confirms your assigned IP, create `/usr/local/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <contents of ~/wg-private.key>
Address = 10.10.0.X/24
DNS = 1.1.1.1

[Peer]
PublicKey = UyhLVKy8LvwUqao1Q5N3roNybDaokBWXl/g8eV/VjWQ=
Endpoint = 20.69.100.77:51820
AllowedIPs = 0.0.0.0/0
```

Replace `10.10.0.X` with your assigned IP and paste your private key.

## Step 3: Connect

```bash
sudo wg-quick up wg0
```

Verify you have a US IP:

```bash
curl ifconfig.me
# Should return: 20.69.100.77
```

## Disconnect

```bash
sudo wg-quick down wg0
```

## Troubleshooting

### Tunnel comes up but no internet

Check the handshake status. If `transfer` shows 0 B received, packets aren't reaching the server:

```bash
sudo wg show
```

Test basic UDP connectivity (with tunnel down):

```bash
nc -u -w 3 20.69.100.77 51820 <<< "test"
```

If it hangs with no response, something local is blocking outbound UDP — check your firewall or any VPN/network software.
