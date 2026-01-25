# Lab Device Credentials

> Note: These are LAB credentials only. Production credentials are in CyberArk.

## Network Devices (Cisco)

**Standard Lab Login**:
- Username: `labadmin`
- Password: `LabTest123!`
- Enable: `EnableLab!`

**Applies to**: Lab-FW-01, Lab-SW-01, Lab-SW-02, R1, R2, R3

## Linux Servers (SRV1, SRV2)

**SSH Access**:
- Username: `sysadmin`
- Password: `LinuxLab2025`
- sudo: same password

**SSH Key Location**: `\\fileserver\it\lab\ssh_keys\lab_id_rsa`

## Windows Server (SRV3)

**RDP Access**:
- Username: `Administrator`
- Password: `WinLab2025!`
- Domain: `LAB.ACMECO.LOCAL`

## Service Accounts

| Service | Username | Password | Purpose |
|---------|----------|----------|---------|
| Ansible | ansible_svc | AnsibleLab! | Automation |
| SNMP | - | community: `labsnmp` | Monitoring |
| Syslog | - | - | UDP 514 to SRV1 |

## Password Rotation

Lab passwords are rotated quarterly. Last rotation: January 1, 2025.

## Emergency Access

If locked out, contact:
- Tom Bradley (ext. 4501)
- Marcus Green (ext. 4510)

Console cables are in the lab cabinet, shelf 2.
