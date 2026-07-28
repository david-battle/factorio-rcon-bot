# System Administration Notes

This file is a manually loaded record of host-level administration work. It is
not part of Jimbo's runtime instructions.

## Local Tooling

`jq` 1.8.1 was installed and verified available in WSL on 2026-07-28.

## OpenClaw Removal

OpenClaw was removed completely on 2026-07-28 after its gateway became stuck in
a restart loop. The installation had two independent startup mechanisms:

- The automatic Windows service `OpenClawGateway`, managed through NSSM.
- The logon scheduled task `OpenClaw Gateway`.

The service launched `C:\Users\dlbat\.openclaw\gateway.cmd`, which ran the global
npm `openclaw` package as a Node gateway on TCP port `18789`. Its service logs
were under `C:\tmp\openclaw`. The scheduled task launched
`C:\Users\dlbat\.openclaw\gateway.vbs`.

Cleanup performed:

- Disabled and deleted the service and scheduled task.
- Terminated the surviving gateway `cmd.exe` and `node.exe` process tree.
- Uninstalled global npm package `openclaw@2026.7.1`.
- Deleted `C:\Users\dlbat\.openclaw`, including credentials, configuration,
  Telegram state, memory, agents, workspaces, and SQLite databases.
- Deleted `C:\tmp\openclaw`, which contained roughly two million crash logs.
- Removed the now-unused NSSM installation.
- Confirmed there were no OpenClaw firewall rules or environment variables.
- Removed the temporary privileged cleanup script.

Final verification found no OpenClaw service, scheduled task, process, command
shim, npm package, state directory, log directory, firewall rule, or listener on
port `18789`.

### Telegram Cleanup

The OpenClaw Telegram bot was deleted through `@BotFather`, invalidating its bot
identity and token. Its retained Telegram chat was then deleted manually. A
future OpenClaw installation should create a new bot and credentials rather than
attempting to recover any part of the old integration.

### Ollama Task Repair

The unrelated `Ollama Serve` scheduled task originally referenced
`C:\Users\dlbat\.openclaw\ollama-serve.cmd`. Because complete OpenClaw cleanup
removed that directory, the task was changed to launch Ollama directly:

```text
Executable: C:\Users\dlbat\AppData\Local\Programs\Ollama\ollama.exe
Arguments:  serve
```

The repaired task was verified in the `Ready` state, and `ollama.exe ps`
responded successfully. Do not recreate Ollama startup files under an OpenClaw
directory.

## Factorio Network Incident

On 2026-07-28, remote Factorio players were disconnected while loopback access
continued to work later. The dedicated server itself remained running and
Windows Firewall retained enabled inbound UDP `34197` rules for all profiles.
The host kept LAN address `192.168.0.109`, its DHCP reservation, and the same
public IP.

The old Factorio log and Windows event logs established this timeline:

- `01:56:36`: Factorio removed the remaining remote peers.
- `01:56:49`: Factorio reported connection resets and DNS resolution failures.
- `01:57:06`: Windows NCSI reported `SuspectDnsProbeFailed`.
- `01:57:30`: WLAN AutoConfig detected limited connectivity and reset the Intel
  Wi-Fi 6 AX201 adapter.
- `01:57:54`: Wi-Fi reassociated with SSID `Casanova`.
- `01:57:55`: DHCP restored reserved address `192.168.0.109`.
- `01:58:15`: Windows confirmed Internet connectivity was restored.

The immediate trigger was therefore a temporary loss of the host's Wi-Fi network
path, not a Factorio crash, firewall change, DHCP address change, or missing port
forward. Plausible underlying causes are a brief router/WAN interruption or an
Intel AX201/access-point data-path stall. Windows initiated the adapter reset as
recovery after connectivity had already failed.

Factorio had originally advertised an automatically discovered public UDP port.
After connectivity returned, it resumed matchmaking heartbeats without repeating
public-address discovery, leaving its old advertised NAT endpoint stale. A clean
server restart performed fresh discovery and registered a new endpoint. Static
UDP `34197` forwarding and the DHCP reservation were already configured; they do
not preserve active sessions through a host or WAN outage.

For better server reliability, prefer wired Ethernet. If Wi-Fi remains necessary,
keep the Intel AX201 driver current and consider disabling adapter power saving.
For a recurrence, preserve the Factorio log and inspect these Windows logs before
restarting:

- `Microsoft-Windows-WLAN-AutoConfig/Operational`
- `Microsoft-Windows-NCSI/Operational`
- `Microsoft-Windows-NetworkProfile/Operational`
- `Microsoft-Windows-Dhcp-Client/Admin`
- The Windows System log, especially `Netwtw10` events

## Credential Follow-Up

During the network investigation, existing RCON and Factorio authentication
credentials were displayed in diagnostic tool output. Rotate the RCON password
and Factorio service token if that has not already been done. Do not record their
values in this repository.
