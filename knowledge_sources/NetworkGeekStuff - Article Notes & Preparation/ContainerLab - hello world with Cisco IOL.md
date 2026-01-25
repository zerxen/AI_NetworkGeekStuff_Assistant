	1) install WSL on your windows PC or get your favorite linux installed directly on your PC, both works
	2) install containerlab using guide on https://containerlab.dev/install/ or simply run in linux command line this:
	   `curl -sL https://containerlab.dev/setup | sudo -E bash -s "all"`
	
	3) Get yourself Cisco IOL images either from Cisco Modelling Labs (CML) if you are paying for that access, or there are some alternative sources our there like https://github.com/hegdepavankumar/Cisco-Images-for-GNS3-and-EVE-NG  but honestly these alternative sources are always very much out of date and you are better off using the free tier of CML.  much better option is to use CML and there  get Cisco IOL images from CML (Cisco Modeling Labs) for free, you download the refplat ISO file (Reference Platform) from Cisco Software Central using a free Cisco account, then mount this refplat IOS and you can find the virl base images inside. 
	   
	   NOTE: Cisco IOL are cisco IOS images compiled for x86 systems and are not real production firmware that you can load to a cisco device, but they are perfect for a lab because we can convert them to VM or containers and run with very little resources, e.g. one cisco IOS canrun on something like 1cpu and just 768MB RAM so gives you ability to run large typologies.
	   
	4) Now we need to convert the images from .bin to images that we can load to docker images repository that container labs is using, for that we will convert it using vrnet provided code. First download the conversion code either manually from  https://github.com/hellt/vrnetlab.git or just use
	   `git clone https://github.com/hellt/vrnetlab.git`
	   
	   now enter into the download code and locate subdirectory vrnetlab/cisco/iol and I placed there two images and renamed them to the internal version name that vrnetlab wanted x86_64_crb_linux-adventerprisek9-ms to cisco_iol-17.16.01a.bin
	x86_64_crb_linux_l2-adventerprisek9-ms.bin to cisco_iol-l2-17.16.01a.bin
	
	then enter the cisco/iol directory and run "make docker-image" that will compile thes eto docker format and place them to docker image inventory, if you are successfull you can check these using "docker image" command like this:
	
	luciola@DESKTOP-9QTU7PP:/mnt/c/Workspace/vrnetlab/cisco/ios$ docker images
	REPOSITORY              TAG            IMAGE ID       CREATED              SIZE
	vrnetlab/cisco_iol      l2-17.16.01a   49d4ddb34cb3   About a minute ago   615MB
	vrnetlab/cisco_iol      17.16.01a      7242831d593a   About a minute ago   713MB
	
	1)  Generic ubuntu VM for lab use
	   One extra thing that we will use here is that we will also use an ubuntu , inside the vrnetlab git directories you already downloaded, there is a ubuntu directory so let's enter that vrnetlab/ubuntu and you will see it includes "download.sh" script, this will download from ubuntu repositories the official qcow2 VM image and we can use "make" to convert this to docker image so lets run these two :
	   
	   download.sh
	   make
	   
	   afterwards using docker image you should see ubuntu there
	   
	luciola@DESKTOP-9QTU7PP:/mnt/c/Workspace/vrnetlab/ubuntu$ docker images
	REPOSITORY                  TAG            IMAGE ID       CREATED          SIZE
	vrnetlab/canonical_ubuntu   jammy          9bcd5086894f   53 seconds ago   965MB
	vrnetlab/cisco_iol          l2-17.16.01a   49d4ddb34cb3   23 minutes ago   615MB
	vrnetlab/cisco_iol          17.16.01a      7242831d593a   24 minutes ago   713MB
	   
	2) Excelent, now we have images for a cisco L3, cisco L2 and a ubuntu acting as endpoint for our leb, lets create a simple topology file  for a simpel topology like this:
	
	ubuntu1 - cisco1 - cisco2 - ubuntu2
	
	And here is the topology file yml:
	
	name: two_ubuntus_via_cisco_IOL_L3
	
	topology:
	  nodes:
	    ubuntu1:
	      kind: generic_vm
	      image: vrnetlab/canonical_ubuntu:jammy
	    ubuntu2:
	      kind: generic_vm
	      image: vrnetlab/canonical_ubuntu:jammy  
	    cisco1:
	      kind: cisco_iol
	      image: vrnetlab/cisco_iol:17.16.01a
	      startup-config: |
	        interface GigabitEthernet0/0
	         ip address      
	    cisco2:
	      kind: cisco_iol
	      image: vrnetlab/cisco_iol:17.16.01a
	      startup-config: |
	        interface GigabitEthernet0/0
	         ip address
	  links:
	    - endpoints: ["cisco1:Ethernet0/2", "ubuntu1:eth1"]  
	    - endpoints: ["cisco1:Ethernet0/1","cisco2:Ethernet0/1"] 
	    - endpoints: ["cisco2:Ethernet0/2", "ubuntu2:eth1"] 
	
	3) And lets execute this now using command: containerlab deploy ./two_ubuntus_via_cisco_IOL_L3.clab.yaml 
	   
	If everything works, you will get a table with two ubuntus and two cisco machines running. 
	
	luciola@DESKTOP-9QTU7PP:/mnt/c/Workspace/containerlabs/two_ciscos$ containerlab deploy ./two_ubuntus_via_cisco_IOL_L3.clab.yaml 
	00:22:12 INFO Containerlab started version=0.72.0
	00:22:12 INFO Parsing & checking topology file=two_ubuntus_via_cisco_IOL_L3.clab.yaml
	00:22:12 INFO Creating lab directory path=/mnt/c/Workspace/containerlabs/two_ciscos/clab-two_ubuntus_via_cisco_IOL_L3
	00:22:12 INFO unable to adjust Labdir file ACLs: operation not supported
	00:22:12 INFO Creating container name=ubuntu2
	00:22:12 INFO Creating container name=ubuntu1
	00:22:12 INFO Creating container name=cisco2
	00:22:12 INFO Creating container name=cisco1
	00:22:15 INFO Created link: cisco1:eth2 (Ethernet0/2) ▪┄┄▪ ubuntu1:eth1
	00:22:15 INFO Created link: cisco2:eth2 (Ethernet0/2) ▪┄┄▪ ubuntu2:eth1
	00:22:15 INFO Running postdeploy actions for Cisco IOL 'cisco2' node
	00:22:15 INFO Created link: cisco1:eth1 (Ethernet0/1) ▪┄┄▪ cisco2:eth1 (Ethernet0/1)
	00:22:15 INFO Running postdeploy actions for Cisco IOL 'cisco1' node
	00:22:15 INFO Adding host entries path=/etc/hosts
	00:22:15 INFO Adding SSH config for nodes path=/etc/ssh/ssh_config.d/clab-two_ubuntus_via_cisco_IOL_L3.conf
	╭───────────────────────────────────────────┬─────────────────────────────────┬────────────────────┬───────────────────╮
	│                    Name                   │            Kind/Image           │        State       │   IPv4/6 Address  │
	├───────────────────────────────────────────┼─────────────────────────────────┼────────────────────┼───────────────────┤
	│ clab-two_ubuntus_via_cisco_IOL_L3-cisco1  │ cisco_iol                       │ running            │ 172.20.20.5       │
	│                                           │ vrnetlab/cisco_iol:17.16.01a    │                    │ 3fff:172:20:20::5 │
	├───────────────────────────────────────────┼─────────────────────────────────┼────────────────────┼───────────────────┤
	│ clab-two_ubuntus_via_cisco_IOL_L3-cisco2  │ cisco_iol                       │ running            │ 172.20.20.4       │
	│                                           │ vrnetlab/cisco_iol:17.16.01a    │                    │ 3fff:172:20:20::4 │
	├───────────────────────────────────────────┼─────────────────────────────────┼────────────────────┼───────────────────┤
	│ clab-two_ubuntus_via_cisco_IOL_L3-ubuntu1 │ generic_vm                      │ running            │ 172.20.20.3       │
	│                                           │ vrnetlab/canonical_ubuntu:jammy │ (health: starting) │ 3fff:172:20:20::3 │
	├───────────────────────────────────────────┼─────────────────────────────────┼────────────────────┼───────────────────┤
	│ clab-two_ubuntus_via_cisco_IOL_L3-ubuntu2 │ generic_vm                      │ running            │ 172.20.20.2       │
	│                                           │ vrnetlab/canonical_ubuntu:jammy │ (health: starting) │ 3fff:172:20:20::2 │
	╰───────────────────────────────────────────┴─────────────────────────────────┴────────────────────┴───────────────────╯
	
	Now we can nicelly connect to the lab using SSH for example to cisco1 device as : ssh admin@clab-two_ubuntus_via_cisco_IOL_L3-cisco1 
	
	Summary:
	In this article this is a super quick overview how to get cisco lab working using much more compart form using containers and control topology using yml files, for more details on topology files and containerlab system visit containerlab.dev as all I did here was just followed their documentaiton and got the images from Cisco 