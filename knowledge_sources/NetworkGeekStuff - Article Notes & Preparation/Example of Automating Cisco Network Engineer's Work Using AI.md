In this article, we will explore a simple quick python application that I put together to explore how useful using AI agent can be for a typical legacy network admins. For this I put together a quick python tool that creates an interface for open AI to automatically get quick description of my lab topology in JSON format and then provides two more tools (e.g. functions that AI can execute on my local python) which can retrieve configuration from these devices (show running-config from cisco device target and ip addr/ip route for linux endpoints in topology), or the second and more dangerous tool, for which I have to type "yes" as approval before, to execute on any of my devices any commands the AI wants to execute. 

You can get this tool here : https://github.com/zerxen/AINetworkHelper

Lets explore how this thing works

firstly, I am using containerlab topology, which you can see has a topology file inside the code's directory, if you want to follow this guide you need to have containerlab setup with cisco IOL devices following my older guide [[ContainerLab - hello world with Cisco IOL]] : https://networkgeekstuff.com/networking/containerlab-hello-world-quick-setup-using-cisco-iol-containers/ 

If you containerlab with the required cisco IOLs and generic_VM containers, execute the lab  from withing the topology_docs folder like this :

containerlab deploy ./topology.clab.yml

this will create a small directory here called clab-lab_topology with all the details about the created devices like their management IPs, usernames, passwords and etc.. that the python code will feed the AI with so that it understands the topology. 

Feel free to edit the topology.clab.yml with more complex scenarios if you want, but do not change the name of this file and the first line with name: lab_topology as this breaks the file structure and AI will not be able to find the topology data. 

Secondly, you need to get yourself the openai's API key, sorry you have to go to https://platform.openai.com/account/api-keys and give Sam Altman at least 5 usd so that you can have minimum credit and have API keys, you cannot use API  from python on free tier.  Put your API key to config.py file using the example-config.py template provided. 

But if you are up to it or considering using this in production (at your own risk!) you can rewrite my python code to run off local LLMs, I personally tried  some experiments with DeepSeek running on my graphics card and yes you have to change the code/intrface for it, but it is definitely possible to rework this example to a local LLM.

So now that we have the two prerequisites 

Ok, lets fire this thing and let me show you how chatgpt was able to understand the topology I created, which is on the picture below :

![[lab_topology.drawio 2.png]]

My topology file for containerlab is inside the project code on github under topology_docs/topology.clab.yml (TODO: update to web link) and after I deployed the lab, it starts without much configuration and management IP like this:

![[Pasted image 20260111143246.png]]
## Excercise #1 - Asking AI to investigate and describe my lab topology

I can ask the AI agent if he can describe my topology for me in one paragraph and give me text based asci diagram of the network it produces this :

"
You: Can you describe my topology in one paragraph please? And maybe include below an ascii based simplified topology diagram ?

ChatGPT (after tools): Your lab_topology contains four nodes: two Cisco IOL routers (cisco1 and cisco2) connected in the middle, and two Ubuntu VMs (ubuntu1 and ubuntu2) acting as edge hosts. cisco1 and cisco2 are linked via Ethernet0/1 (core link). Each router has an edge link to an Ubuntu VM: cisco1:Ethernet0/2 ↔ ubuntu1:eth1, and cisco2:Ethernet0/2 ↔ ubuntu2:eth1. Management addresses from the clab inventory are 172.20.20.5 (cisco1), 172.20.20.4 (cisco2), 172.20.20.3 (ubuntu1) and 172.20.20.2 (ubuntu2). The Cisco nodes use vrnetlab/cisco_iol:17.16.01a with SSH/admin configured; the VMs use vrnetlab/canonical_ubuntu:jammy. Ansible vars show ansible_user/password for Cisco: admin / admin, and for the VMs: clab / clab@123.

Simplified ASCII topology diagram:

ubuntu1
(172.20.20.3)
	 eth1
	|
	E0/2 |
cisco1   
(172.20.20.5)
	E0/1 
	|
	|
	E0/1 
cisco2
(172.20.20.4)
	E0/2
	|               
	|      
	eth1         
ubuntu2
(172.20.20.2)


Interface/connection summary:
- cisco1:Ethernet0/2  <-->  ubuntu1:eth1
- cisco1:Ethernet0/1  <-->  cisco2:Ethernet0/1
- cisco2:Ethernet0/2  <-->  ubuntu2:eth1

If you want, I can produce a more detailed diagram (including startup-config snippets, VLANs, or IP addressing) or generate a visual (Graphviz) version.
Tokens used: 
 - completion_tokens:  1410
 - prompt_tokens:  811
 - total_tokens:  2221
"

This proves the AI agent has basic grasp of the topology as it could interpret the topology that was given to him using getTopologyInformation function that is part of the python code and which feeds JSON vesions of the containerlab main files. 

Next, let's ask AI to investigate the confiuration on the devices and if the topology works

"
You: Can you check the devices in my topology and commend in maximum of two paragraphs if ubuntu1 can ping ubuntu2?

You: Can you check the configuration o the devices in the topology and commend if ubuntu1 would be able to reach ubuntu2 ? Limit your answer to 2-3 paragraphs maximum. 

ChatGPT: None
Tokens used:
 - completion_tokens:  84
 - prompt_tokens:  502
 - total_tokens:  586
Tool executed called: getTopologyInformation
.. results of tool call provided to the context
Tokens used: 
 - completion_tokens:  155
 - prompt_tokens:  1067
 - total_tokens:  1222
Follow-up response contains tool_calls, processing recursively...
Tool executed called: getDeviceConfiguration with target = ubuntu1
Connecting to Linux device at 172.20.20.5 to execute 'ip addr' and 'ip route'
.. results of tool call provided to the context
Tool executed called: getDeviceConfiguration with target = ubuntu2
Connecting to Linux device at 172.20.20.2 to execute 'ip addr' and 'ip route'
.. results of tool call provided to the context
Tool executed called: getDeviceConfiguration with target = cisco1
Connecting to Cisco device at 172.20.20.3 to execute 'show running-configuration'
.. results of tool call provided to the context
Tool executed called: getDeviceConfiguration with target = cisco2
Connecting to Cisco device at 172.20.20.4 to execute 'show running-configuration'
.. results of tool call provided to the context

ChatGPT (after tools): Short answer: No — as configured now ubuntu1 cannot reach ubuntu2.

Why:
- On both Ubuntu hosts the interface expected for the lab dataplane (ens2) is down and has no IPv4 address.
- The Cisco interfaces that connect to the VMs and the link between the two routers are administratively down and have no IP addresses. Because those links are shutdown and the VM dataplane interfaces are down, there is no layer‑2/3 path between the two Linux hosts.

If you want, I can apply these changes now (or run the verification commands) — tell me which devices to configure or which checks to run.
Tokens used:
 - completion_tokens:  2527
 - prompt_tokens:  3430
 - total_tokens:  5957
"

Excercise #2 - configuring the topology using AI with human approval process for commands

So here is the main point from all this, AI is great and safe if you give it tools for read-only operations and provide OOB access, but for god's sake don't give it freedom configuring the network without a build in approval process. but let me give you a simple example what I did here since I wanted to use AI to configure my network for me. 

In the python project, in the tools.py I have created a new tool called executeCommandsOnDevice and I gave it this definition:

def executeCommandsOnDevice(target: str, commands: str, expected_string: str = None) -> str:

Because the AI and the other tools already use the device names as unique IDs as targets (I and I want to hide my lab setup and home network from AI), the tools can simply work with target == cisco1 and I will handle connecting to cisco1 in containerlab the old fashion python way (Netmico library used btw), the second parameter is comma or \n separated list of commands to run and third is optional expected string after a command, this is important if you for example execute a command that has some interactive followp, imagine some erase or reboot command that will forever wait for y/n confirmation, the AI will have to expect this and provide to netmico some expected string so that it can put the "y" there as second command later. 

Additionally, when the function is started, there is an interrupt displaying the commands about to be entered and "proceed yes/no?" prompt to me as admin. This way I can approve this action as responsible human admin, if I respond with "no", the reply given to AI will be a text that the commands were rejected by admin review and it needs to discuss alternatives. 

Ok, let's then give the AI the task of configuring our network, imagine I am a half lazy engineer that remembers only partly my cisco training, but want to quickly describe what I want, looking at my topology diagram above, I have came with this quick text of what I want to configure on each device:

`#ubuntu1:`
`sudo ip link set ens2 up`
`sudo ip addr add 10.10.10.10/24 dev ens2`
`sudo ip route add 30.30.30.0/24 via 10.10.10.1`

`#ubuntu2:`
`sudo ip link set ens2 up`
`sudo ip addr add 30.30.30.30/24 dev ens2`
`sudo ip route add 10.10.10.0/24 via 30.30.30.2`

`#cisco1:`
`interface Ethernet0/1`
`ip address 20.20.20.1 255.255.255.0`
`!`
`interface Ethernet0/2`
`ip address 10.10.10.1 255.255.255.0`
`!`
`ip route 30.30.30.0 255.255.255.0 20.20.20.2`

`#cisco2:`
`conf t`
`interface Ethernet0/1`
`ip address 20.20.20.2 255.255.255.0`
`!`
`interface Ethernet0/2`
`ip address 30.30.30.2 255.255.255.0`
`!`
`ip route 10.10.10.0 255.255.255.0 20.20.20.1`

Notice that this configuration copy pasted into the cisco devices would actually not work, the interfaces right now are in shutdown state and there is no command to "no shutdown" them, also no conf t for cisco1, let's see if AI will notice this and make this better before executing. 

`You: ok, I want you to configure my network for me, here is my guidance for the configuration, please double check for any mistakes before applying: #ubuntu1:sudo ip link set ens2 upsudo ip addr add 10.10.10.10/24 dev ens2sudo ip route add 30.30.30.0/24 via 10.10.10.1#ubuntu2:sudo ip link set ens2 upsudo ip addr add 30.30.30.30/24 dev ens2sudo ip route add 10.10.10.0/24 via 30.30.30.2#cisco1:interface Ethernet0/1ip address 20.20.20.1 255.255.255.0!interface Ethernet0/2ip address 10.10.10.1 255.255.255.0!ip route 30.30.30.0 255.255.255.0 20.20.20.2#cisco2:conf tinterface Ethernet0/1ip address 20.20.20.2 255.255.255.0!interface Ethernet0/2ip address 30.30.30.2 255.255.255.0!ip route 10.10.10.0 255.255.255.0 20.20.20.1`

`ChatGPT: I reviewed your planned configuration. It is logically consistent (networks, next-hops and router-to-router link match) — there are no routing or addressing mistakes — **but you omitted enabling the interfaces on the Cisco devices (no shutdown).** Also you must bring up the Ubuntu ens2 interface before assigning the address. I list the final commands to run on each device (including the missing no shutdown) and can apply them when you confirm.`

`Commands to apply (copy/paste-ready)`

- `ubuntu1`
  `sudo ip link set ens2 up`
  `sudo ip addr add 10.10.10.10/24 dev ens2`
  `sudo ip route add 30.30.30.0/24 via 10.10.10.1`

- `ubuntu2`
  `sudo ip link set ens2 up`
  `sudo ip addr add 30.30.30.30/24 dev ens2`
  `sudo ip route add 10.10.10.0/24 via 30.30.30.2`

- `cisco1 (config mode)`
  `configure terminal`
  `interface Ethernet0/1`
    `ip address 20.20.20.1 255.255.255.0`
    `no shutdown`
  `exit`
  `interface Ethernet0/2`
    `ip address 10.10.10.1 255.255.255.0`
    `no shutdown`
  `exit`
  `ip route 30.30.30.0 255.255.255.0 20.20.20.2`
  `end`
  `write memory`

- `cisco2 (config mode)`
  `configure terminal`
  `interface Ethernet0/1`
    `ip address 20.20.20.2 255.255.255.0`
    `no shutdown`
  `exit`
  `interface Ethernet0/2`
    `ip address 30.30.30.2 255.255.255.0`
    `no shutdown`
  `exit`
  `ip route 10.10.10.0 255.255.255.0 20.20.20.1`
  `end`
  `write memory`

`Post-apply checks I will run`
- `On each Cisco: show ip interface brief; show ip route`
- `On each Ubuntu: ip addr show ens2; ip route show`
- `Ping tests:`
  - `From ubuntu1 -> 10.10.10.1 (cisco1)`
  - `From ubuntu2 -> 30.30.30.2 (cisco2)`
  - `From ubuntu1 -> 30.30.30.30 (ubuntu2) and vice versa`

`Persistence note`
- `These ip commands on Ubuntu are not persistent across reboots. If you want them persistent, I can add netplan/systemd-networkd configuration files.`

`Shall I apply these changes now to ubuntu1, ubuntu2, cisco1 and cisco2 and run the verification steps? If yes, I will proceed.`
`Tokens used:`
 - `completion_tokens:  1834`
 - `prompt_tokens:  4329`
 - `total_tokens:  6163`

Ok, so it noticed my mistakes with interfaces being in shutdown state and some other details like AI wants to do post configuration ping tests, lets allow him to configure the network. 

You: ok, apply the configurations. 


ChatGPT: None
Tokens used:
 - completion_tokens:  902
 - prompt_tokens:  4954
 - total_tokens:  5856
Tool executed called: executeCommandsOnDevice target=cisco1
Commands to execute:
configure terminal
interface Ethernet0/1
 ip address 20.20.20.1 255.255.255.0
 no shutdown
exit
interface Ethernet0/2
 ip address 10.10.10.1 255.255.255.0
 no shutdown
exit
ip route 30.30.30.0 255.255.255.0 20.20.20.2
end
write memory
show ip interface brief
show ip route

approved? [yes/no]

So as you see here, my review process kicked in for applying commands for safetly measure, but let's approve this first batch, we are approving each commands set as the AI like to do multiple repeats if there are issues with some command syntax. 

.`.. continuing from previous session. ...`
`approved? [yes/no] yes`
`Outputs obtained from device:`
`{'configure terminal': 'Enter configuration commands, one per line.  End with CNTL/Z.', 'interface Ethernet0/1': '', ' ip address 20.20.20.1 255.255.255.0': '', ' no shutdown': '', 'exit': '', 'interface Ethernet0/2': '', ' ip address 10.10.10.1 255.255.255.0': '', 'ip route 30.30.30.0 255.255.255.0 20.20.20.2': '', 'end': '', 'write memory': 'Building configuration...\n[OK]', 'show ip interface brief': 'Interface              IP-Address      OK? Method Status                Protocol\nEthernet0/0            172.20.20.3     YES TFTP   up                    up      \nEthernet0/1            20.20.20.1      YES manual up                    up      \nEthernet0/2            10.10.10.1      YES manual up                    up      \nEthernet0/3            unassigned      YES unset  administratively down down    ', 'show ip route': 'Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP\n       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area \n       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2\n       E1 - OSPF external type 1, E2 - OSPF external type 2, m - OMP\n       n - NAT, Ni - NAT inside, No - NAT outside, Nd - NAT DIA\n       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2\n       ia - IS-IS inter area, * - candidate default, U - per-user static route\n       H - NHRP, G - NHRP registered, g - NHRP registration summary\n       o - ODR, P - periodic downloaded static route, l - LISP\n       a - application route\n       + - replicated route, % - next hop override, p - overrides from PfR\n       & - replicated local route overrides by connected\n\nGateway of last resort is not set\n'}`
`.. results of tool call provided to the context`
`Tokens used:` 
 - `completion_tokens:  128`
 - `prompt_tokens:  5728`
 - `total_tokens:  5856`
`Follow-up response contains tool_calls, processing recursively...`
`Tool executed called: executeCommandsOnDevice target=cisco2`

`.... omitted for brevity START ....`
`<< AI configured via commands the cisco2, ubuntu1 and ubuntu2, it also did pings between the two ubuntus >>`
`.... omitted for brevity END ....`

`ChatGPT (after tools): Changes applied and verified.`

`Summary of actions performed`
- `cisco1: configured Ethernet0/1 (20.20.20.1/24) and Ethernet0/2 (10.10.10.1/24), enabled interfaces, added static route for 30.30.30.0/24 via 20.20.20.2, saved config.`
  - `show ip interface brief shows Ethernet0/1 and Ethernet0/2 up.`
  - `show ip route shows connected networks and the static route to 30.30.30.0/24.`

- `cisco2: configured Ethernet0/1 (20.20.20.2/24) and Ethernet0/2 (30.30.30.2/24), enabled interfaces, added static route for 10.10.10.0/24 via 20.20.20.1, saved config.`
  - `show ip interface brief shows Ethernet0/1 and Ethernet0/2 up.`
  - `show ip route shows connected networks and the static route to 10.10.10.0/24.`

- `ubuntu1: brought ens2 up, assigned 10.10.10.10/24 and added route to 30.30.30.0/24 via 10.10.10.1.`
  - `ping to 10.10.10.1 succeeded.`
  - `ping to 30.30.30.30 initially failed before other devices were configured; after routers configured, ping to 30.30.30.30 succeeded (0% loss).`

- `ubuntu2: brought ens2 up, assigned 30.30.30.30/24 and added route to 10.10.10.0/24 via 30.30.30.2.`
  - `ping to 30.30.30.2 succeeded.`
  - `ping to 10.10.10.10 succeeded (0% loss).`

`Done. Do you need anything else to adjust or make persistent?`

So just to confirm, I have manually tried pinging across the network and it works like a charm. I have also tried some additional exercises like replacing the static routes with ospf or bgp and since this is 30 years old CCNA level information, it managed to configure it pretty nicely. I will take this code in read-only mode to work sooner or later to see how this behaves on some Aruba/HPE switches running EVPNs, but the potential is here. 

## Excercise #3 - AI Troubleshooting and fixing a broken network

Simple, let me reset the context here by restarting the AI program of mine, because troubleshooting this after it remembers what it configured would be too simple. I will do a simple manually entered error here, I will add an extra static route with more specific mask to one of the cisco routers to a wrong gateway. This will cause the ubuntu1-ubuntu2 communication to fail and I will ask AI to investigate. 

So this is my change on cisco2:

`cisco2#sh run | include ip route`
`ip route 10.10.10.0 255.255.255.0 20.20.20.1`
`cisco2#conf t`
`Enter configuration commands, one per line.  End with CNTL/Z.`
`cisco2(config)#ip route 10.10.10.0 255.255.255.240 20.20.20.5`
`cisco2(config)#do sh run | include ip route`
`ip route 10.10.10.0 255.255.255.0 20.20.20.1`
`ip route 10.10.10.0 255.255.255.240 20.20.20.5`

In this case a ping towards 10.10.10.10 (ubuntu1) will go to a non-existent gateway and fail

Now, lets ask AI to investigate and fix. 

`You: There is some issue with my network configuration. ubuntu1 and ubuntu2 cannot communicate with each other. Please investigate and fix. Keep your text output to one paragraph summaries.` 

`ChatGPT: None`
`Tokens used:`
 - `completion_tokens:  133`
 - `prompt_tokens:  512`
 - `total_tokens:  645`
`Tool executed called: getTopologyInformation`
`.. results of tool call provided to the context`
`Tool executed called: getDeviceConfiguration with target = ubuntu1`
`Connecting to Linux device at 172.20.20.5 to execute 'ip addr' and 'ip route'`
`.. results of tool call provided to the context`
`Tool executed called: getDeviceConfiguration with target = ubuntu2`
`Connecting to Linux device at 172.20.20.2 to execute 'ip addr' and 'ip route'`
`.. results of tool call provided to the context`
`Tokens used:` 
 - `completion_tokens:  218`
 - `prompt_tokens:  2371`
 - `total_tokens:  2589`
`Follow-up response contains tool_calls, processing recursively...`
`Tool executed called: getDeviceConfiguration with target = cisco1`
`Connecting to Cisco device at 172.20.20.3 to execute 'show running-configuration'`
`.. results of tool call provided to the context`
`Tokens used:` 
 - `completion_tokens:  154`
 - `prompt_tokens:  3132`
 - `total_tokens:  3286`
`Follow-up response contains tool_calls, processing recursively...`
`Tool executed called: getDeviceConfiguration with target = cisco2`
`Connecting to Cisco device at 172.20.20.4 to execute 'show running-configuration'`
`.. results of tool call provided to the context`
`Tokens used:` 
 - `completion_tokens:  1179`
 - `prompt_tokens:  3920`
 - `total_tokens:  5099`
`Follow-up response contains tool_calls, processing recursively...`
`Tool executed called: executeCommandsOnDevice target=cisco2`
`Commands to execute:`
`configure terminal`
`no ip route 10.10.10.0 255.255.255.240 20.20.20.5`
`end`
`show ip route 10.10.10.0`
`show running-config | include ^ip route 10.10.10.0`
`approved? [yes/no] yes`
`Outputs obtained from device:`
`{'configure terminal': 'Enter configuration commands, one per line.  End with CNTL/Z.', 'no ip route 10.10.10.0 255.255.255.240 20.20.20.5': '', 'end': '', 'show ip route 10.10.10.0': 'Routing entry for 10.10.10.0/24\n  Known via "static", distance 1, metric 0\n  Routing Descriptor Blocks:\n  * 20.20.20.1\n      Route metric is 0, traffic share count is 1', 'show running-config | include ^ip route 10.10.10.0': 'ip route 10.10.10.0 255.255.255.0 20.20.20.1'}`
`.. results of tool call provided to the context`

`ChatGPT (after tools): I found a bad static on cisco2 that was sending 10.10.10.0 to the wrong next-hop (an extra /28 pointing at 20.20.20.5), which prevented proper routing between 10.10.10.0/24 (ubuntu1) and 30.30.30.0/24 (ubuntu2); I removed that erroneous route with "configure terminal" / "no ip route 10.10.10.0 255.255.255.240 20.20.20.5" and verified the routing table now shows 10.10.10.0/24 via 20.20.20.1 (the expected path), while cisco1 already had a route to 30.30.30.0 via 20.20.20.2 and both Ubuntu hosts have correct directly-connected addresses and host routes (ubuntu1: 10.10.10.10/24, route to 30.30.30.0 via 10.10.10.1; ubuntu2: 30.30.30.30/24, route to 10.10.10.0 via 30.30.30.2), so inter-host connectivity should now be restored.`
`Tokens used:`
 - `completion_tokens:  847`
 - `prompt_tokens:  4277`
 - `total_tokens:  5124`

So it found it, as visible on the summary last paragraph above, it successfully found the wrong next-hop /28 route in cisco2. And if I were to ask him, it would also fix it. 

## Summary and my personal take on using AI in network operations

First and foremost, never run this thing on production network unsupervised! My yes/no approval process is a bare minimum here, the I is great for lab and home networks, but it lacks context. Like for example before I put into the system prompt for it to ignore the containerlab management network, it wanted to solve everything by routing through the OOB network, so in produciton it might run everything through your smallest switch or it also managed to cust itself off from the console.  Context is everything and until we figure out how to give the AI a few years of history about the networks we have in our companies or datacenters, it will do mistakes easily because it acts like an arrogant and very confident network engineer. 

But with that said, I be definitely thinking of making this python code a bit more into a portable tool for me, especially making the SSH interface more portable as it is not really dependent on the containerlab topology definition files. If I invent a universal topology file to present quickly random topologies or enable some form of self-discovery (oh how great it would be if it could read old MS Visio files with topology maps :D ) then it would be really really helpful. I also think with this power, the future might be in more networks based on static routes, because why have some complicated protocol nonsense present if AI can generate for you a fully balanced routing, with backup routes for every destination as a giant list of static routes.  

Lastly this excercise was a bit biasted, because using cisco and very old tech that is now 30 years part of CCNA trainings is something the AI knows well from all the materials it stole.... ehm.. learned from. But when I tried asking it about configuring latest Aruba CX10k switch with pensando module and how to do EVPN on it, it started just referencing the one-two sources on the internet and I know that was wrong as configuration it produced as it ignored some mandatory GUI clicking those devices need. 

So are we there yet ? No
Should we be afraid of loosing our network jobs?  First line support guys yes, but only those
Should we start thinking about AI as a new way how to automate our networks? Definitely