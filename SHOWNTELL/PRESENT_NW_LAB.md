## First make sure you have access to WSL contianerlab

route add 172.20.20.0 mask 255.255.255.0 172.27.67.220

wsl:
# Enable forwarding for this session
sudo sysctl -w net.ipv4.ip_forward=1

# Allow forwarding in iptables
sudo iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT
sudo iptables -t nat -A POSTROUTING -s 172.20.20.0/24 -j MASQUERADE
To make ip_forward persist across WSL restarts, add it to /etc/sysctl.conf:

# persistent
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.conf

## Credentials to machines:

*   **ubuntu1**:
    *   **Username**: `clab`
    *   **Password**: `clab@123`

*   **cisco1**:
    *   **Username**: `admin`
    *   **Password**: `admin`

## Configuration PROMPT:
I want you to configure the network and all devices in the topology, 
please configure on 
ubuntu1 an IP address 10.10.10.10/24 on ens2, and a static route for 30.30.30.0/24 via the cisco1 next hop IP.  
ubuntu2 with IP address 30.30.30.30/24 on ens2, and a static route for 10.10.10.0/24 via the cisco2 next hop IP.  
Transit network between cisco1 and cisco2 is 20.20.20.0/24 with cisco1 using .1 on transit and cisco2 using .2 on transit subnet
Do not remove the default routes from ubuntu1 and ubuntu2 towards mgmt network, use only new static routes to achieve this. 

## OSPF Reconfigure 
Reconfigure the routing on cisco1 and cisco2 to be using OSPF, make sure ubuntu1 and ubuntu2 can still ping each other

## Break the conneciton by inserting wrong static route
e.g. 
cisco2(config)#ip route 10.10.10.0 255.255.255.192 20.20.20.3

PROMPT (bad): 
I cannot ping ubuntu1 from ubuntu2, can you troubleshoot why ?

PROMPT (good): 
I cannot ping ubuntu1 from ubuntu2, can you troubleshoot why ? ubuntu1 and ubuntu2 are configured correctly, focus exclusivelly on cisco switches. 

## BGP Reconfigure 
Reconfigure the routing on cisco1 and cisco2 to be using BGP, make sure ubuntu1 and ubuntu2 can still ping each other