
## Purpose
The network lab is used for testing configurations, training, and proof-of-concept work before production deployment for Acmeco customer.

## Location
- Building A, Room 105 (basement level)
- Badge access required (request from Bob Stevens, Facilities)

## Lab Network Topology
![[images\lab_topology.png]]

## Device Inventory

| Hostname | Model                        | Management IP | Purpose            |
| -------- | ---------------------------- | ------------- | ------------------ |
| Cisco1   | Cisco 2610 router            | 172.16.1.1    | Router for testing |
| Cisco2   | Cisco 2610 router            | 172.16.2.1    | Router for testing |
| Ubuntu1  | Virtual Machine on ESX1 host | 172.16.1.10   | Linux VM           |
| Ubuntu2  | Virtual Machine on ESX2 host | 172.16.1.11   | Linux VM           |


## Access Instructions

1. Connect to VPN (GlobalProtect)
2. SSH/RDP to management IPs listed above
3. Credentials in password manager under "Lab Devices" folder

## Important Notes

- Lab is isolated from production network
- Internet access via NAT through Lab-FW-01
- Power cycles every Sunday 2AM for maintenance
- Contact Tom Bradley for lab reservations
