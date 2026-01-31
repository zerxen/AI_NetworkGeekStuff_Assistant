modprobe --first-time bonding
modinfo bonding

Create a file named /etc/sysconfig/network-scripts/ifcfg-bond0

      DEVICE="bond0"
      IPADDR=3.3.3.254
      NETMASK=255.255.255.0
      NETWORK=3.3.3.0
      BROADCAST=3.3.3.255
      ONBOOT=yes
      BOOTPROTO=none
      USERCTL=no
      TYPE=Ethernet
      BONDING_OPTS="mode=1 miimon=100 fail_over_mac=active"
      
      
OTHER INTERFACES ifcfg-ethX

      DEVICE=eth0
      BOOTPROTO=none
      ONBOOT=yes
      MASTER=bond0
      SLAVE=yes
      USERCTL=no
      NM_CONTROLLED=no
      
Create the file /etc/modprobe.d/bonding.conf

      alias bond0 bonding 
      # options bond0 mode=1 miimon=100
           
ACTIVATE
      
      service network restart
      
STATUS CHECK

      cat /proc/net/bonding/bond0  