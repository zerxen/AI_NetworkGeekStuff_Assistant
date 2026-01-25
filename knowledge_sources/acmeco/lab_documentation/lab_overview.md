# ACME Co Network Lab Overview

## Purpose
The network lab is used for testing configurations, training, and proof-of-concept work before production deployment.

## Location
- Building A, Room 105 (basement level)
- Badge access required (request from Bob Stevens, Facilities)

## Lab Network Topology

```
                    [Internet]
                        |
                   [Lab-FW-01]
                   172.16.0.1
                        |
            +-----------+-----------+
            |                       |
       [Lab-SW-01]            [Lab-SW-02]
       172.16.1.1             172.16.2.1
            |                       |
     +------+------+         +------+------+
     |      |      |         |      |      |
   [R1]   [R2]   [R3]     [SRV1] [SRV2] [SRV3]
```

## Device Inventory

| Hostname | Model | Management IP | Purpose |
|----------|-------|---------------|---------|
| Lab-FW-01 | Cisco ASA 5506 | 172.16.0.1 | Lab firewall |
| Lab-SW-01 | Cisco 2960X | 172.16.1.1 | Access switch |
| Lab-SW-02 | Cisco 2960X | 172.16.2.1 | Server switch |
| R1 | Cisco CSR1000v | 172.16.1.10 | Router for testing |
| R2 | Cisco CSR1000v | 172.16.1.11 | Router for testing |
| R3 | Cisco CSR1000v | 172.16.1.12 | Router for testing |
| SRV1 | Ubuntu 22.04 VM | 172.16.2.10 | Ansible control node |
| SRV2 | Ubuntu 22.04 VM | 172.16.2.11 | Docker host |
| SRV3 | Windows Server 2022 | 172.16.2.12 | AD test server |

## Access Instructions

1. Connect to VPN (GlobalProtect)
2. SSH/RDP to management IPs listed above
3. Credentials in password manager under "Lab Devices" folder

## Important Notes

- Lab is isolated from production network
- Internet access via NAT through Lab-FW-01
- Power cycles every Sunday 2AM for maintenance
- Contact Tom Bradley for lab reservations
