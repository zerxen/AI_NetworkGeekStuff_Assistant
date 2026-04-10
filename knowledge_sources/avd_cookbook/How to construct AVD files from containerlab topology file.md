# AVD Single DC L3LS Cookbook

This cookbook contains Jinja2 templates and step-by-step instructions for generating a complete
Arista AVD (Ansible AVD) configuration set for a single data center L3LS (Layer 3 Leaf-Spine)
EVPN/VXLAN fabric, starting from a ContainerLab topology file.

---

## What Is AVD and What Files Does It Need?

Arista AVD (Arista Validated Designs) is an Ansible collection that generates EOS device
configurations from a set of structured YAML input files. For a single DC L3LS design the
required inputs are:

| File | Purpose |
|---|---|
| `inventory.yml` | Ansible inventory: groups all devices into spine/leaf/fabric groups |
| `group_vars/FABRIC.yml` | Fabric-wide settings: routing protocols, BGP passwords, NTP, DNS, users |
| `group_vars/DC1.yml` | DC-level settings: management gateway, eAPI |
| `group_vars/DC1_SPINES.yml` | Spine node definitions: IDs, loopbacks, BGP AS |
| `group_vars/DC1_L3_LEAVES.yml` | L3 leaf MLAG pair definitions: IDs, BGP AS, uplinks, IP pools |
| `group_vars/DC1_L2_LEAVES.yml` | L2 leaf definitions (optional, omit if none) |
| `group_vars/NETWORK_SERVICES.yml` | VRFs, SVIs (anycast gateways), L2-only VLANs |
| `group_vars/CONNECTED_ENDPOINTS.yml` | Server/host port assignments |
| `playbooks/build.yml` | Ansible playbook to generate configs |
| `playbooks/deploy.yml` | Ansible playbook to push configs via eAPI |

Templates for all of these files are in the `templates/` subdirectory alongside this README.
Each template is a `.j2` file. The top of every template contains a comment block listing
every variable it uses and what it expects.

---

## How to Use These Templates: Step-by-Step

When asked to generate AVD files for a topology, follow these steps in order.

### Step 1 — Parse the ContainerLab Topology File

Read the provided `.clab.yaml` file. Extract:

1. **All node names and their kinds** (e.g. `cisco_iol`, `arista_ceos`, `linux`, `generic_vm`).
2. **All links** — each link has two endpoints in the form `nodename:interfacename`.
3. **Management IPs** — ContainerLab assigns these from its `mgmt` network block, or they may
   be listed in a generated `topology-data.json`. If not explicitly given, you may need to ask
   the user or assign them from a reasonable range like `172.20.20.0/24`.

### Step 2 — Classify Devices into Roles

Use the link topology to determine each device's role:

- **Spine**: devices that have links to MANY other devices (especially leaf devices) and are
  NOT connected to servers/endpoints. In a spine-leaf design spines connect only to leaves.
  Devices with "spine" in their name are almost certainly spines.
- **L3 Leaf**: devices connected to spines AND optionally to L2 leaves or servers. Devices
  with "leaf" in their name and uplinks going to spines are L3 leaves.
- **L2 Leaf**: devices connected only to L3 leaves (not to spines directly). They provide
  additional access ports. Devices named e.g. `leaf1c` that connect only to `leaf1a`/`leaf1b`
  are L2 leaves.
- **MLAG Pair**: two L3 (or L2) leaves that connect to the SAME set of spines and share a
  direct peer-link between them are an MLAG pair. They share one BGP AS.

If the topology has no L2 leaves, skip all L2 leaf templates entirely.

### Step 3 — Assign Numeric IDs

AVD uses integer IDs to calculate IP addresses from pools. Assign them as follows:

- **Spine IDs**: number spines 1, 2, 3... in order.
- **L3 Leaf IDs**: number ALL L3 leaf nodes globally (not per-pair): 1, 2, 3, 4...
  Nodes in the first pair get IDs 1 and 2, second pair get 3 and 4, etc.
- **L3 Leaf loopback offset**: set `loopback_ipv4_offset` to the number of spines so that
  leaf loopbacks don't overlap spine loopbacks in the shared pool.
  Example: 2 spines → offset = 2, so spine1=.1, spine2=.2, leaf1a=.3, leaf1b=.4 ...
- **L2 Leaf IDs**: number within each group starting at 1 (IDs reset per group).
- **BGP AS**: spines share one AS. Each L3 MLAG pair gets its own AS.
  A common scheme: spines = 65100, pair1 = 65101, pair2 = 65102, etc.

### Step 4 — Choose IP Address Pools

If the user provides IP pools, use those. Otherwise use these safe defaults:

| Pool | Default | Purpose |
|---|---|---|
| `spine_loopback_pool` | `10.255.0.0/27` | Spine and leaf loopback0 (shared, offset applied) |
| `l3leaf_vtep_pool` | `10.255.1.0/27` | Leaf VTEP loopback1 (loopback for VXLAN source) |
| `l3leaf_uplink_pool` | `10.255.255.0/26` | P2P /31 links between leaves and spines |
| `l3leaf_mlag_peer_pool` | `10.255.1.64/27` | MLAG peer-link VLAN4094 addresses |
| `l3leaf_mlag_peer_l3_pool` | `10.255.1.96/27` | iBGP between MLAG peers |

### Step 5 — Fill in the Templates

For each template file listed in the table above, produce the corresponding output YAML by
substituting all `{{ variable }}` placeholders and evaluating all `{% for %}` / `{% if %}`
blocks. The variable comment block at the top of each template explains every placeholder.

**Important rules when filling templates:**

- `spine_names` in `DC1_L3_LEAVES.yml.j2` must be a YAML list of spine node name strings,
  e.g. `['dc1-spine1', 'dc1-spine2']`.
- `uplink_switches` in `DC1_L2_LEAVES.yml.j2` must list the two L3 nodes of the matching
  MLAG pair, e.g. `['dc1-leaf1a', 'dc1-leaf1b']`.
- Management IPs must include the prefix length, e.g. `172.20.20.11/24`.
- Do NOT render the `{% comment %}` variable-description block in the output — strip it.
  The output files should only contain valid YAML.
- If a conditional block (`{% if ... %}`) evaluates to false for this topology (e.g. no
  L2 leaves, no CloudVision), omit that block entirely from the output.

### Step 6 — Handle Network Services and Endpoints

The `NETWORK_SERVICES.yml` and `CONNECTED_ENDPOINTS.yml` templates define the overlay
services (VRFs, VLANs, server ports). These are NOT derived from the ContainerLab topology —
they describe the customer workloads running on the fabric.

- If the user has not specified VRFs/VLANs, generate a minimal example with one tenant,
  one VRF (`VRF10`), and two SVIs (VLAN 11 and VLAN 12).
- If the user has not specified servers, generate one example server entry per L3 leaf MLAG
  pair showing a dual-homed trunk connection (LACP bond) and one single-homed access port.
- Always ask the user to review these files before deployment, as they describe business logic.

### Step 7 — Output File Layout

Place the generated files in this directory structure:

```
<project>/
├── inventory.yml
├── group_vars/
│   ├── FABRIC.yml          (ansible connectivity + fabric settings)
│   ├── DC1.yml
│   ├── DC1_SPINES.yml
│   ├── DC1_L3_LEAVES.yml
│   ├── DC1_L2_LEAVES.yml   (omit if no L2 leaves)
│   ├── NETWORK_SERVICES.yml
│   └── CONNECTED_ENDPOINTS.yml
└── playbooks/
    ├── build.yml
    └── deploy.yml
```

Note: `FABRIC.yml` in AVD typically also holds the ansible connection variables from
`ansible_connectivity.yml.j2`. You can either merge them into one file or keep them separate
as `group_vars/all/ansible.yml`.

---

## Key AVD Concepts to Keep in Mind

**MLAG (Multi-chassis Link Aggregation)**
Two leaf switches act as one logical switch toward servers. They share a peer-link
(typically Ethernet3-4 per the default_interfaces template) and a virtual IP. AVD handles
all MLAG configuration automatically from the node_group definition.

**EVPN/VXLAN Overlay**
The fabric runs BGP EVPN as the overlay control plane. Spines are route reflectors.
Each leaf has a VTEP (VXLAN Tunnel Endpoint) on loopback1. MAC and IP routes are distributed
via EVPN address families. AVD generates all of this from the node IDs and IP pools.

**BGP Underlay**
Point-to-point eBGP runs on the P2P /31 links between spines and leaves. Each leaf pair has
its own BGP AS. AVD calculates the /31 addresses from `uplink_ipv4_pool` using node IDs.

**Loopback Address Calculation**
AVD computes loopback0 addresses as: `loopback_pool` base + `id` + `loopback_ipv4_offset`.
This is why spine and leaf IDs must be consistent with the offset value.

**VRF VNI and MAC-VRF VNI**
- `vrf_vni` is the L3 VNI for inter-VRF routing (used on symmetric IRB).
- `mac_vrf_vni_base` + VLAN ID = the L2 VNI for each VLAN. Keep base high enough that
  `base + highest_vlan_id` does not exceed 16 million.

---

## Common Mistakes to Avoid

- **Duplicate IDs**: L3 leaf IDs must be unique across the entire fabric, not just per pair.
  If pair1 has IDs 1,2 and pair2 also has IDs 1,2 — address collisions will occur.
- **Wrong uplink_switches**: L3 leaves must list spine names, not other leaves.
  L2 leaves must list their parent L3 MLAG pair nodes, not spines.
- **Loopback pool overlap**: if spines use IDs 1-2 and `loopback_ipv4_offset` is 0, then
  leaf IDs 1-2 will collide with spine IDs 1-2 in the same pool. Always set the offset
  equal to the number of spines.
- **MTU mismatch**: for cEOSLab/vEOS use MTU 1500. For hardware Arista switches use 9214.
  Change `p2p_uplinks_mtu` in FABRIC.yml accordingly.
- **Missing NETWORK_SERVICES group membership**: the `NETWORK_SERVICES` and
  `CONNECTED_ENDPOINTS` groups in `inventory.yml` must include all leaf groups that carry
  tenant traffic. L3 and L2 leaves are typically both members.

---

## Example: Mapping a 2-Spine / 4-Leaf ContainerLab Topology

Given this ContainerLab links section:
```yaml
links:
  - endpoints: ["spine1:Ethernet1", "leaf1a:Ethernet1"]
  - endpoints: ["spine1:Ethernet2", "leaf1b:Ethernet2"]
  - endpoints: ["spine1:Ethernet3", "leaf2a:Ethernet1"]
  - endpoints: ["spine1:Ethernet4", "leaf2b:Ethernet2"]
  - endpoints: ["spine2:Ethernet1", "leaf1a:Ethernet2"]
  - endpoints: ["spine2:Ethernet2", "leaf1b:Ethernet1"]
  - endpoints: ["spine2:Ethernet3", "leaf2a:Ethernet2"]
  - endpoints: ["spine2:Ethernet4", "leaf2b:Ethernet1"]
  - endpoints: ["leaf1a:Ethernet3", "leaf1b:Ethernet3"]  # MLAG peer-link
  - endpoints: ["leaf2a:Ethernet3", "leaf2b:Ethernet3"]  # MLAG peer-link
```

Derive:
- **Spines**: `spine1`, `spine2` — each connects to all 4 leaves → spine role.
- **L3 MLAG Pair 1**: `leaf1a` (id=1) + `leaf1b` (id=2), BGP AS 65101 — both connect to both
  spines and share a peer-link.
- **L3 MLAG Pair 2**: `leaf2a` (id=3) + `leaf2b` (id=4), BGP AS 65102.
- **loopback_ipv4_offset**: 2 (because there are 2 spines using IDs 1 and 2).
- **spine_names**: `['spine1', 'spine2']` for the `uplink_switches` default in L3_LEAVES.

---

## Template File Index

| Template | Generates | Required? |
|---|---|---|
| `templates/inventory.yml.j2` | `inventory.yml` | Always |
| `templates/group_vars/FABRIC.yml.j2` | `group_vars/FABRIC.yml` | Always |
| `templates/group_vars/ansible_connectivity.yml.j2` | Merge into FABRIC.yml or separate | Always |
| `templates/group_vars/DC1.yml.j2` | `group_vars/DC1.yml` | Always |
| `templates/group_vars/DC1_SPINES.yml.j2` | `group_vars/DC1_SPINES.yml` | Always |
| `templates/group_vars/DC1_L3_LEAVES.yml.j2` | `group_vars/DC1_L3_LEAVES.yml` | Always |
| `templates/group_vars/DC1_L2_LEAVES.yml.j2` | `group_vars/DC1_L2_LEAVES.yml` | Only if L2 leaves exist |
| `templates/group_vars/NETWORK_SERVICES.yml.j2` | `group_vars/NETWORK_SERVICES.yml` | Always |
| `templates/group_vars/CONNECTED_ENDPOINTS.yml.j2` | `group_vars/CONNECTED_ENDPOINTS.yml` | Always |
| `templates/playbooks/build.yml.j2` | `playbooks/build.yml` | Always |
| `templates/playbooks/deploy.yml.j2` | `playbooks/deploy.yml` | Always |
