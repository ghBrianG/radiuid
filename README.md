# RadiUID ![RadiUID][logo]

An application to extract User-to-IP mappings from RADIUS accounting data and send them to Palo Alto firewalls for use by the User-ID function.


-----------------------------------------
## VERSION
The version of RadiUID documented here is: **v3.0.0**

**Original Author:** John W Kerns (PackeTsar) – All versions through v2.5.0
**v3.0.0 Maintainer:** Brian Griffith – Python 3 port and continued development

This is a fork of the [original RadiUID project](https://github.com/PackeTsar/radiuid) with Python 3 support and additional features.


-----------------------------------------
## TABLE OF CONTENTS
1. [What is RadiUID?](#what-is-radiuid)
2. [How it Works](#how-it-works)
3. [Examples](#examples)
4. [Requirements](#requirements)
5. [Tested Environments](#tested-environments)
6. [Docker Install Instructions](#docker-install-instructions)
7. [OS Install Instructions](#os-install-instructions)
8. [Pip/Wheel Installation](#pipwheel-installation)
9. [Command Interface](#command-interface)
10. [Timeout Tuning](#timeout-tuning)
11. [The Munge Engine](#the-munge-engine)
12. [NPS/Windows Log Support](#npswindows-log-support)
13. [Live Log Processing](#live-log-processing)
14. [Network Mount Dependencies](#network-mount-dependencies)
15. [Updates](#updates)
16. [Upgrade Processes](#upgrade-processes)
17. [Docker Files](#dockerfiles)
18. [Contributing](#contributing)


-----------------------------------------
## WHAT IS RADIUID?
User-based firewall filtering is a novel and attractive concept that can often be challenging to implement due to the requirement by firewalls to map IP addresses to users. One common method of getting user-to-IP mapping information for your firewall is to install a log-reading agent onto an Active Directory domain controller which can look over transaction logs and send the proper information to the firewall. However, this assumes user endpoints interact and authenticate directly with the domain controllers, and that you have Active Directory!

RadiUID is a Linux application designed to capture routine RADIUS accounting data from authentication devices such as wireless networks and firewalls, which includes user and IP address details. This ephemeral IP-to-username mapping data is then transmitted to a Palo Alto firewall for utilization by its User-ID feature, enabling user or group-specific access control and sophisticated reporting.


--------------------------------------
## HOW IT WORKS
RadiUID uses FreeRADIUS as a backend service to listen on RADIUS accounting ports (typically TCP/UDP 1813) and write the received accounting information to accounting logs.

RadiUID then parses these logs, extracts the user and IP mapping information, and pushes those mappings to the Palo Alto firewall using the published RESTful XML API.

RadiUID runs as a system service on Linux and is straightforward to configure and use. All configuration and interaction with RadiUID is via the command line in the Linux Bash shell. Once the installer completes, RadiUID can be invoked from the command shell by typing `radiuid` followed by the desired command. Press the [TAB] key for command options or press [ENTER] for the list of options!


--------------------------------------

## EXAMPLES

**The main list of CLI command options (`radiuid`)**

```
$ radiuid
-------------------------------------------------------------------------------------------------------------------------------
                     ARGUMENTS                    |                                  DESCRIPTIONS
-------------------------------------------------------------------------------------------------------------------------------

 - run                                            |  Run the RadiUID main program in shell mode
-------------------------------------------------------------------------------------------------------------------------------

 - install                                        |  Run RadiUID Install/Maintenance Utility
-------------------------------------------------------------------------------------------------------------------------------

 - show log                                       |  Show the RadiUID log file
 - show acct-logs                                 |  Show the log files in the FreeRADIUS accounting directory
 - show livelog                                   |  Show the live log file settings
 - show nps                                       |  Show the NPS CSV column settings
 - show config (yaml | set)                       |  Show the RadiUID configuration
 - show clients (file | table)                    |  Show the FreeRADIUS clients
 - show status                                    |  Show the RadiUID and FreeRADIUS service statuses
 - show mappings (<target> | all | consistency)   |  Show the current IP-to-User mappings
-------------------------------------------------------------------------------------------------------------------------------

 - set <option> <value>                           |  Set configuration options
 - push (<target> | all) <user> <ip>              |  Manually push a User-ID mapping
 - clear <option>                                 |  Clear logs, mappings, or configuration
 - service <service> <action>                     |  Control RadiUID and FreeRADIUS services
 - request <action>                               |  Request system operations
-------------------------------------------------------------------------------------------------------------------------------

 - version                                        |  Show the current version of RadiUID
-------------------------------------------------------------------------------------------------------------------------------
```

**Output from the `show log` command**

```
$ radiuid show log
================================================================================
                              RADIUID LOG FILE
================================================================================
2025-01-15 10:23:45 INFO     [service] RadiUID service starting...
2025-01-15 10:23:45 INFO     [config_manager] Loaded configuration from /etc/radiuid/radiuid.yaml
2025-01-15 10:23:46 INFO     [service] Found 3 accounting log files to process
2025-01-15 10:23:46 INFO     [data_processor] Processing: detail-20250115
2025-01-15 10:23:46 INFO     [data_processor] Extracted 12 User-ID mappings
2025-01-15 10:23:47 INFO     [palo_alto] Pushing 12 UIDs to firewall01.example.com:vsys1
2025-01-15 10:23:47 INFO     [palo_alto] Successfully pushed UIDs to firewall01.example.com:vsys1
2025-01-15 10:23:47 INFO     [service] Sleeping for 10 seconds...
```

**Output from the `show config` command (YAML format)**

```
$ radiuid show config
paths:
  radius_log_path: /var/log/freeradius/radacct/
  log_file: /etc/radiuid/radiuid.log
  acct_log_copy_path: null

logging:
  max_log_lines: 10000

uid_settings:
  user_domain: MYDOMAIN
  timeout: 60

misc:
  loop_time: 10
  tls_version: '1.2'
  radius_stop_action: clear

targets:
  firewall01.example.com:vsys1:
    hostname: firewall01.example.com
    vsys: '1'
    username: radiuid-api
    password: '********'
    port: '443'
```

**Output from the `show config set` command**

```
$ radiuid show config set
radiuid set logfile /etc/radiuid/radiuid.log
radiuid set radiuslogpath /var/log/freeradius/radacct/
radiuid set maxloglines 10000
radiuid set userdomain MYDOMAIN
radiuid set timeout 60
radiuid set looptime 10
radiuid set tlsversion 1.2
radiuid set radiusstopaction clear
radiuid set target firewall01.example.com:1 username radiuid-api
radiuid set target firewall01.example.com:1 password ********
radiuid set target firewall01.example.com:1 port 443
radiuid set client 10.0.0.0/8 mysecretkey
radiuid set client 192.168.1.0/24 anothersecret
```

**Pushing a mapping and viewing mappings**

```
$ radiuid push firewall01.example.com:vsys1 jsmith 10.1.50.100
Pushing UID mapping: jsmith -> 10.1.50.100 to firewall01.example.com:vsys1
Successfully pushed UID mapping

$ radiuid show mappings firewall01.example.com:vsys1
================================================================================
              USER-ID MAPPINGS: firewall01.example.com:vsys1
================================================================================
USER                                     IP ADDRESS        TIMEOUT
--------------------------------------------------------------------------------
MYDOMAIN\jsmith                          10.1.50.100       58 min
MYDOMAIN\bgriffith                       10.1.50.101       45 min
MYDOMAIN\asmith                          10.1.50.102       32 min
--------------------------------------------------------------------------------
Total: 3 mappings
```

**Test munge rules with `request munge-test`**

```
$ radiuid request munge-test "DOMAIN\\\\username" debug
########################## MUNGE TEST ##########################
################################################################

Processing input: DOMAIN\\username

Rule 101.0: match "\\\\.*" partial -> MATCHED
  Step 101.10: set-variable domain from-match "^[a-zA-Z0-9]+" -> "DOMAIN"
  Step 101.20: set-variable user from-match "[a-zA-Z0-9]+$" -> "username"
  Step 101.30: set-variable slash from-string "\\" -> "\"
  Step 101.40: assemble domain slash user -> "DOMAIN\username"

String input from command line:  DOMAIN\\username

String returned by Munge Engine: DOMAIN\username

################################################################
################################################################
```


--------------------------------------
## REQUIREMENTS
OS:			**Any modern Debian, RHEL distro (CentOS 7+, Ubuntu 18+, Rocky Linux, AlmaLinux), or Docker container host**

Interpreter:		**Python 3.8+** *(Migrated from Python 2.7.X in v3.0.0)*

PAN-OS Version:		**6.X, 7.X, 8.X, 9.X, 10.X, and 11.X**

Dependencies:        **PyYAML** - `pip3 install pyyaml` (for YAML configuration)


--------------------------------------
## TESTED ENVIRONMENTS
RadiUID has been written and tested in a few environments to date as it was purpose-built for a specific environment, but it should be very adaptable as it uses standardized RADIUS accounting to source user information and the published API to push that info into Palo Alto firewalls.

RadiUID has currently been tested with the following Operating Systems, RADIUS servers, and authenticators:

Operating Systems: **CentOS 7, CentOS 6, Ubuntu 16 Server, Ubuntu 14 Server, Docker 1.10.3**

Identity Systems: **JumpCloud RADIUS service, Windows 2012 NPS Server (with Active Directory)**

Authenticators: **Meraki Wireless Access Points, Cisco Wireless (Controller-based), Ruckus Zonedirector**


----------------------------------------------
## DOCKER INSTALL INSTRUCTIONS

> **Note:** The pre-built Docker images on Docker Hub (`packetsar/radiuid`) are from the original project and only
> support **v2.5.0** (Python 2.7). They do not yet support v3.0.0. To run RadiUID v3.0.0 in Docker, you must build your
> own image using the Dockerfiles in the [Docker Files](#dockerfiles) section below.

Downloading and running RadiUID on a Docker host is the fastest and easiest way to get it up and running. There are two versions of the RadiUID image maintained on Docker Hub: an image **with SSH**, and an image **without SSH**. The image **with SSH** has the SSH server installed and pre-configured with a login username and password. All you have to do is change the password. The Dockerfile build scripts that were used to build the images are available in the [Docker Files](#dockerfiles) section in case you want to perform the build yourself.

**Using Pre-built Images (v2.5.0 only):**

1. From the Docker host, download and run the image in interactive mode
	1. To run the image **with SSH**: `docker run -it -p 1813:1813/udp -p 1813:1813/tcp -p 222:22/tcp --name radiuid -t packetsar/radiuid-ssh:latest`
	2. To run the image **without SSH**: `docker run -it -p 1813:1813/udp -p 1813:1813/tcp --name RADIUID -t packetsar/radiuid:latest`
2. *If you ran the image with SSH:* The default SSH username and password is root/radiuid. Run the command `passwd root` to change the SSH password.
	1. *NOTE: The command above to run the container with SSH publishes the SSH service on TCP port 222. You will need to connect to that port with your SSH client to get access to the container.*
3. Run the command `radiuid show config set` to see the default configuration.
4. Run the `radiuid clear target all` command to delete the firewall target configurations, then use the `radiuid set target [parameters]` command to configure the application with your Palo Alto target firewall parameters.
5. Run the `radiuid set client [parameters]` command to configure FreeRADIUS to accept RADIUS accounting data from your RADIUS authenticators.
6. Once configuration is complete, run the `radiuid service all restart` command to restart the services so the new configuration takes effect.
7. Take a look at your logs using the `radiuid show log` command to see what the application is doing.
8. To exit your interactive session with the Docker container, hold down `CTRL` and hit `P` then `Q`.



----------------------------------------------
## OS INSTALL INSTRUCTIONS
The installation of RadiUID is quick and straightforward using the built-in installer.
NOTE: You need to be logged in as root or have sudo privileges on the system to install RadiUID.

1. Install the OS with the appropriate IP and system settings and update to the latest patches (recommended).
	- Check out the [CentOS Minimal Server - Post-Install Setup][centos-post-install] and the [Ubuntu Server - Post Install Setup][ubuntu-post-install] for help with some of the post-OS-install configuration steps.
2. Install the Git client (unless you already have the RadiUID files): `sudo yum install git -y` or `sudo apt install git -y`.
3. Clone the RadiUID repo to any location on the box: `git clone https://github.com/ghBrianG/radiuid.git`.
4. Change to the directory where the RadiUID main code file (radiuid.py) and the config file (radiuid.yaml) are stored:
   `cd radiuid`
	- (OPTIONAL) Change to the development branch (perform this step only if you are prepared for a version that is under active development and may have broken features): `git checkout devX.X.X`.
5. Run the RadiUID program in installation mode to perform the installation: `sudo python3 radiuid.py install`.
    - NOTE: Make sure that you have the config file (radiuid.yaml or examples/radiuid.yaml.sample) in the same directory
      for the initial installation.
6. Follow the on-screen prompts to install FreeRADIUS and the RadiUID application.
	- The installer should indicate whether everything was installed correctly and services are running. In the next section, you will find CLI commands you can run to check on it.

----------------------------------------------

## PIP/WHEEL INSTALLATION

RadiUID v3.0.0 can be installed using pip and a wheel file. This is the recommended method for production deployments as
it provides better isolation and easier upgrades.

**Building the Wheel File:**

If you have the source code and need to build the wheel:

```bash
# Install build tools
pip3 install build

# Build the wheel (creates dist/radiuid-3.0.0-py3-none-any.whl)
python3 -m build
```

**Installing with a Virtual Environment (Recommended):**

Using a virtual environment isolates RadiUID from system Python packages and avoids conflicts.

```bash
# Create a virtual environment at /opt/radiuid
sudo python3 -m venv /opt/radiuid

# Install the wheel file
sudo /opt/radiuid/bin/pip install radiuid-3.0.0-py3-none-any.whl

# Verify installation
/opt/radiuid/bin/radiuid version
```

**Creating a Symlink for Easy Access:**

```bash
# Create symlink so 'radiuid' works from anywhere
sudo ln -sf /opt/radiuid/bin/radiuid /usr/local/bin/radiuid

# Now you can run radiuid directly
radiuid version
```

**Installing the Service:**

After pip installation, you need to install the systemd service:

```bash
# Run the installer to set up the service and config
sudo /opt/radiuid/bin/radiuid install

# Or do a quick reinstall if config already exists
sudo /opt/radiuid/bin/radiuid request reinstall keep-config
```

**Upgrading:**

To upgrade to a new version:

```bash
# Stop the service
sudo systemctl stop radiuid

# Install the new wheel (use --force-reinstall to ensure clean upgrade)
sudo /opt/radiuid/bin/pip install radiuid-3.1.0-py3-none-any.whl --force-reinstall

# Reinstall service files (keeps your config)
sudo radiuid request reinstall keep-config

# Restart the service
sudo systemctl start radiuid
```

**Direct pip Install (Alternative):**

You can also install directly from the source directory:

```bash
# From the radiuid source directory
sudo /opt/radiuid/bin/pip install .

# Or install in development mode (changes take effect immediately)
sudo /opt/radiuid/bin/pip install -e .
```

----------------------------------------------
## COMMAND INTERFACE
The RadiUID system is meant to run in the background as a system service—constantly checking for new RADIUS accounting data and pushing User-ID mapping information to the firewall—but it also has an easy-to-use command interface. This command interface is intended for regular maintenance, troubleshooting, and operation of the system.

Below is the CLI guide for the RadiUID service.

*You can see this guide by typing `python3 radiuid.py` (before installation) or `radiuid` (after installation) and pressing [ENTER].*
```
-------------------------------------------------------------------------------------------------------------------------------
                     ARGUMENTS                    |                                  DESCRIPTIONS
-------------------------------------------------------------------------------------------------------------------------------

 - run                                            |  Run the RadiUID main program in shell mode to begin pushing User-ID information
-------------------------------------------------------------------------------------------------------------------------------

 - install                                        |  Run RadiUID Install/Maintenance Utility
-------------------------------------------------------------------------------------------------------------------------------

 - show log                                       |  Show the RadiUID log file
 - show acct-logs                                 |  Show the log files currently in the FreeRADIUS accounting directory
 - show livelog                                   |  Show the current live log processing settings and status
 - show nps                                       |  Show the NPS CSV column settings (ip, username, packet-type)
 - show run (yaml | set)                          |  Show the RadiUID configuration in YAML format (default) or as `set` commands
 - show config (yaml | set)                       |  Show the RadiUID configuration in YAML format (default) or as `set` commands
 - show clients (file | table)                    |  Show the FreeRADIUS clients and the config file
 - show status                                    |  Show the RadiUID and FreeRADIUS service statuses
 - show mappings (<target> | all | consistency)   |  Show the current IP-to-User mappings for one or all targets, or check consistency
-------------------------------------------------------------------------------------------------------------------------------

 - set logfile                                    |  Set the RadiUID log file path
 - set radiuslogpath <directory path>             |  Set the path used to find FreeRADIUS accounting log files
 - set acctlogcopypath <directory path>           |  Set the path where RadiUID should copy accounting log files before deletion
 - set maxloglines <number-of-lines>              |  Set the maximum number of lines allowed in the log ('0' turns circular logging off)
 - set userdomain (none | <domain name>)          |  Set the domain name prepended to User-ID mappings
 - set timeout                                    |  Set the timeout (in minutes) for User-ID mappings sent to the firewall targets
 - set looptime                                   |  Set the waiting loop time (in seconds) to pause between checks of the RADIUS logs
 - set tlsversion (1.0 | 1.1 | 1.2)               |  Set the version of TLS used for XML API communication with the firewall targets
 - set radiusstopaction (clear | ignore | push)   |  Set the action taken by RadiUID when RADIUS stop messages are received
 - set client (ipv4|ipv6) <ip-block> <secret>     |  Set configuration elements for RADIUS clients to send accounting data to FreeRADIUS
 - set munge <rule>.<step> [parameters]           |  Set munge (string-processing rules) for User-IDs
 - set target <hostname>:<vsys-id> [parameters]   |  Set configuration elements for existing or new firewall targets
 - set livelog <option> <value>                   |  Configure live log file processing (file, tracker, enabled)
 - set nps ip-column <number>                     |  Set NPS CSV column index for IP address (0-indexed, -1 for auto)
 - set nps username-column <number>               |  Set NPS CSV column index for username (0-indexed, -1 for auto)
 - set nps packet-type-column <number>            |  Set NPS CSV column index for packet type (0-indexed)
-------------------------------------------------------------------------------------------------------------------------------

 - push (<hostname>:<vsys-id> | all) [parameters] |  Manually push a User-ID mapping to one or all firewall targets
-------------------------------------------------------------------------------------------------------------------------------

 - tail log (<# of lines>)                        |  Watch the RadiUID log file in real time
-------------------------------------------------------------------------------------------------------------------------------

 - clear log                                      |  Delete the contents of the log file
 - clear acct-logs                                |  Delete the log files currently in the FreeRADIUS accounting directory
 - clear livelog tracker                          |  Reset the live log position tracker to re-read from the beginning
 - clear client (<ip-block> | all)                |  Delete one or all RADIUS client IP blocks in the FreeRADIUS config file
 - clear munge (<rule> | all) (<step> | all)      |  Delete one or all munge rules in the config file
 - clear target (<hostname>:<vsys-id> | all)      |  Delete one or all firewall targets in the config file
 - clear mappings [parameters]                    |  Remove one or all IP-to-User mappings from one or all firewalls
-------------------------------------------------------------------------------------------------------------------------------

 - edit config                                    |  Edit the RadiUID config file
 - edit clients                                   |  Edit the RADIUS client config file for FreeRADIUS
-------------------------------------------------------------------------------------------------------------------------------

 - service [parameters]                           |  Control the RadiUID and FreeRADIUS system services
-------------------------------------------------------------------------------------------------------------------------------

 - request xml-update                             |  Update the Python `xml.etree` modules
 - request munge-test <string> (debug)            |  Test and debug the Munge Engine using a provided string
 - request auto-complete                          |  Manually install the RadiUID Bash auto-completion feature
 - request freeradius-install (no-confirm)        |  Manually install the FreeRADIUS service
 - request reinstall (replace|keep)-config        |  Reinstall RadiUID with or without replacing the current configuration
 - request uninstall (keep|remove)-config         |  Uninstall RadiUID from the system
 - request set-mount (<mount-path> | none)        |  Configure a network mount dependency for the RadiUID service
-------------------------------------------------------------------------------------------------------------------------------

 - version                                        |  Show the current version of RadiUID and FreeRADIUS
-------------------------------------------------------------------------------------------------------------------------------
```


----------------------------------------------
## TIMEOUT TUNING
RadiUID pushes ephemeral User-ID information to the firewall whenever new RADIUS accounting information is received and, by default, sets a timeout of 60 minutes. If this accounting information comes from a wireless system (where most devices re-authenticate regularly), then you may be able to reduce that timeout to make the mapping information expire more quickly. If the RADIUS authenticator is something like a VPN concentrator (where re-authentication typically doesn't happen), then you may want to increase the timeout period. Either way, you should expect to adjust the timeout settings to ensure your firewalls do not prematurely expire User-ID data from their mapping tables.


----------------------------------------------
## THE MUNGE ENGINE
The Munge Engine is a rule-based string processor used in RadiUID to filter and process User-IDs based on rules you configure. The munge feature was introduced in version 2.2.0.

- A sample munge configuration can be seen below. This configuration will instruct the Munge Engine to find any User-ID which contains a double-backslash and reconstruct it with only one backslash. Then it will find any User-ID which contains the name 'vendor' and discard it (prevent it from being pushed to the Palo Alto). This example uses both of the Munge Engine complex actions (`set-variable`, and `assemble`), but only uses one of the simple actions (`discard`), it does not use the `accept` simple action.

    *NOTE: The double-backslash in the `101.0 match` statement is represented by a quad-backslash because Bash recognizes the backslash character as an escape. You will always need to use a double-backslash to represent a single backslash. You also should always wrap your regular expressions in quotes when entering them.*
```
radiuid set munge 101.0 match "\\\\" partial
radiuid set munge 101.10 set-variable domain from-match "^[a-zA-Z0-9]+"
radiuid set munge 101.20 set-variable user from-match "[a-zA-Z0-9]+$"
radiuid set munge 101.30 set-variable slash from-string "\\"
radiuid set munge 101.40 assemble domain slash user
radiuid set munge 102.0 match "vendor" partial
radiuid set munge 102.10 discard
```

- Munge rules are broken down into rules and steps and are configured/ordered in a dot-notation as `<rule number>.<step number>`. The rules and steps can be numbered as desired with one exception (`X.0`) which is described below. The rules and steps are processed in order by their numbers, so when configuring them, you may want to leave gaps in the assigned numbers for insertion of other rules or steps later between the existing ones.
- The only requirement for rule numbering is that step '0' in each rule (X.0) must be a match statement, as it is used to determine whether to process the rule on the User-ID. All rules must begin with a `X.0 match` statement followed by either an `any` keyword (which will match all inputs) or by a regular expression.
	- If the `X.0 match` statement uses a regular expression, it will require a `complete` or `partial` keyword at the end which is used as the return criterion. The `complete` keyword requires that the regular expression match and return the entire input User-ID. The `partial` keyword activates the rule upon a partial return of the input User-ID from the regular expression match operation.
- Other than the required `X.0 match` action, Munge has four actions which are broken down into two groups:
	- Simple Actions: `accept`, `discard`
	- Complex Actions: `set-variable`, `assemble`
- The various actions are explained below
	- The `accept` action halts all rule and step processing and passes the input (User-ID) back out of the engine without any further filtering or changes.
	- The `discard` action halts all rule and step processing and discards the current input; not allowing it to pass out of the engine at all.
	- This command directs the engine to retain a string, which can be derived from the input/User-ID or be a preset static string, in memory for later use by the assemble action. The variable is named immediately following the term and can be any alphanumeric word. The origin of the string can be either a match from a regular expression (via the term) or a string that has been statically set (via the term).
  - *Please be aware that variables designated in one rule can be applied in subsequent rules. The value of a variable, however, will be updated by the most recent rule in which it is used, superseding any prior assignments.*
	- The `assemble` action is used to assemble previously set variables into one string. A list of strings should be provided in order after the `assemble` verb separated by spaces.
- The `request munge-test` command can be used to test a Munge rule-set on a provided input. You can also provide the `debug` term at the end of the command to see a walk-through of the steps taken by the Munge Engine and how it processed the configured rules to modify/filter the input provided in the command.
- The `radiuid push` command has the new keyword `bypass-munge` available at the end to either let the Munge Engine process the input User-ID (by default) or bypass the Munge Engine and push only the input User-ID.


--------------------------------------
## NPS/WINDOWS LOG SUPPORT

Version 3.0.0 adds support for Windows NPS (Network Policy Server) and IAS log formats in addition to FreeRADIUS accounting logs. RadiUID auto-detects the log format and parses accordingly.

**Supported Formats:**

| Format      | Description                             | Auto-Detection            |
|-------------|-----------------------------------------|---------------------------|
| FreeRADIUS  | Standard RADIUS accounting logs         | Default                   |
| NPS XML     | Windows NPS XML format (`<Event>` tags) | Detected by `<Event>`     |
| NPS/IAS CSV | Windows NPS comma-separated format      | Detected by CSV structure |

**NPS XML Format Example:**
```xml
<Event>
    <User-Name data_type="1">jsmith</User-Name>
    <SAM-Account-Name data_type="1">DOMAIN\jsmith</SAM-Account-Name>
    <Framed-IP-Address data_type="3">10.1.50.100</Framed-IP-Address>
    <Packet-Type data_type="0">4</Packet-Type>
</Event>
```

**NPS CSV Format Example:**
```
10.1.50.100,jsmith,12/11/2025,17:05:02,IAS,NPS-SERVER,4,1,0,host/PC001,10.1.50.100
```

**Key Fields:**
- `User-Name` or `SAM-Account-Name` - Username (domain prefix is extracted)
- `Framed-IP-Address` - Assigned IP address
- `Packet-Type` - 4=Accounting-Start, 5=Accounting-Stop

RadiUID will skip records that don't have both a username and an IP address.

**Configuring NPS CSV Column Positions:**

For NPS CSV logs, you can configure which columns contain the IP address, username, and packet type. This is useful when
your NPS logs have a non-standard format or when the IP address is in a different column than expected.

```bash
# View current NPS settings
radiuid show nps

# Set column indices (0-indexed)
radiuid set nps ip-column 39           # Column containing the client IP
radiuid set nps username-column 1      # Column containing the username
radiuid set nps packet-type-column 7   # Column containing the packet type

# Use -1 to enable auto-detection (looks for RADIUS attribute numbers)
radiuid set nps ip-column -1
radiuid set nps username-column -1
```

**Example NPS CSV with Column Numbers:**

```
Col 0       Col 1   Col 2       Col 3     ...  Col 38  Col 39
10.1.75.64, mainc,  12/15/2025, 13:18:50, ..., 8,      10.1.16.142, ...
(NAS IP)    (User)  (Date)      (Time)         (Attr)  (Client IP)
```

In this example:

- Column 0 is the NAS/Access Point IP (not the user's IP)
- Column 1 is the username
- Column 39 is the actual client IP (Framed-IP-Address, attribute 8)
- Column 7 contains the packet type (Acct-Status-Type)

--------------------------------------
## LIVE LOG PROCESSING

For environments where logs are continuously written to a single file (common with NPS), RadiUID supports "live log" processing. Instead of reading and deleting individual log files, RadiUID tracks its position in the file and processes only new entries.

**Configuration:**
```bash
# Set the path to the live log file
radiuid set livelog file /mnt/logs/nps.log

# Set the path for the position tracker file
radiuid set livelog tracker /var/lib/radiuid/tracker

# Enable live log processing
radiuid set livelog enabled on

# View current settings
radiuid show livelog
```

**How It Works:**
1. RadiUID reads from the last known position in the log file
2. New entries are parsed and processed
3. The position is saved to the tracker file
4. On the next loop iteration, only new entries are read

**Reset Tracking:**
```bash
# Reset to re-read from the beginning of the file
radiuid clear livelog tracker
```

**Notes:**
- Live log processing and traditional accounting log processing can run simultaneously
- The tracker file persists across service restarts
- If the log file is rotated/truncated, RadiUID detects this and resets to the beginning


--------------------------------------
## NETWORK MOUNT DEPENDENCIES

If your RADIUS/NPS log files are stored on a network share (NFS, CIFS/SMB), you can configure RadiUID to wait for the mount before starting. This prevents the service from failing if the network share isn't available at boot time.

**During Installation:**

The installation wizard will ask if your log files are on a network share and configure the systemd service accordingly.

**After Installation:**

```bash
# Configure mount dependency
radiuid request set-mount /mnt/accountinglogs

# Remove mount dependency
radiuid request set-mount none
```

**What It Does:**

When configured, the RadiUID systemd service file is updated with:
- `After=network-online.target mnt-accountinglogs.mount`
- `Requires=mnt-accountinglogs.mount`
- `RequiresMountsFor=/mnt/accountinglogs`

This ensures RadiUID only starts after the specified mount point is available.

**Note:** After changing the mount configuration, restart the service:
```bash
radiuid service radiuid restart
```


--------------------------------------
--------------------------------------
## Updates

*Note: All versions through v2.5.0 were developed by John W Kerns (PackeTsar). Brian Griffith maintains version 3.0.0 and later.*


--------------------------------------
### UPDATES IN V1.1.0 --> V2.0.0

**ADDED FEATURES:**

- The RadiUID config file uses YAML format (v3.0+). Legacy XML configurations are automatically migrated to YAML on
  the first load.

- All configuration settings (including the RADIUS client configuration for FreeRADIUS) are configurable using `set` commands. Just type `radiuid set` and hit [ENTER] to see the options or type `show config set` and hit [ENTER] to see the current configuration as a series of `set` commands.

- Multiple target firewalls are now supported; mappings can be pushed to multiple firewalls using different credentials.

- Multi-vsys functionality has been added, so a configured firewall target includes parameters for the target vsys. If you want to control multiple vsys on the same firewall, you will need to add multiple targets.

- Improved HTTP error handling to keep the application from crashing.

- Added CLI auto-complete functionality to allow you to use the [TAB] key to automatically complete commands or see the available options.

- Circular logging was added to maintain the size of the log file. The number of lines allowed in the log file is controlled by the *maxloglines* parameter which is configurable using the `set maxloglines` command.

- The `show mappings` was command added to pull and view mappings directly from one or all firewalls. The `consistency` parameter can also be used to check the consistency of mappings across all configured firewalls.

- The `push` command was added to allow you to manually push a User-to-IP mapping to one or all the firewalls. *NOTE: The user and IP address can be anything you want, they do not have to be legitimate users or working IP addresses*

- The `show config set` command was added to display the current configuration as a series of `set` commands which can be copied and pasted to configure the application.

- The `show clients`, `set client`, and `clear client` commands were added to allow you to more easily control the RADIUS clients configured in the FreeRADIUS clients.conf file. Now it can all be administered using RadiUID commands. The `show config set` output even includes the current RADIUS clients as `set client` commands.

--------------------------------------

### UPDATES IN V2.0.0 --> V2.0.1

**BUG FIXES:**

- *ISSUE #13*: The RadiUID 'merge_dicts' method was throwing a `KeyError` exception and quitting the loop (service) when a FreeRADIUS log was scraped which didn't contain the three required fields (`usernameterm`, `ipaddressterm`, and the `delineatorterm`). An error handler has been added to detect the `KeyError`, dump the dictionary data to the log, and continue in the loop.
    - This issue was reproduced on v2.0.0 code by removing the line in the FreeRADIUS log containing the `usernameterm` text and running the loop (`radiuid run`).
    - It is highly recommended to update to v2.0.1 or later to fix this bug as it affects the stability of the RadiUID RADIUS log capturing functionality.

- *ISSUE #14*: The default configured `delineatorterm` was documented as non-functional for RADIUS accounting messages from a Ruckus wireless system by Dan Hume on his blog at http://www.dhume.co.uk. He had to change the default `delineatorterm` to "Accounting-Session-ID" to make the log parsing work properly.
    - This bug has been fixed by adding functionality for RadiUID to recognize the paragraph separations between FreeRADIUS log entries within the same file and use those paragraph separations as the delineator. To enable this functionality, you must upgrade to v2.0.1 and use the [PARAGRAPH] keyword as the `delineatorterm` value (which is now the default value in the config file).


--------------------------------------
### UPDATES IN V2.0.1 --> V2.1.0

**ADDED FEATURES:**

- Multi-OS support: Previously only CentOS 7 was supported for installation due to dependencies on specific file paths and OS commands for interaction with the OS. Now RadiUID should fully work on any modern Debian or RHEL distro. It has been QA tested on CentOS 7.2, CentOS 6.8, Ubuntu 16.04, and Ubuntu 14.04.

- `radiuid show acct-logs` and `radiuid clear acct-logs` commands now added to help with controlling the FreeRADIUS logs in the accounting directory.

- The new `request` top-level command now gives access to some of the more advanced system-level functions in RadiUID. These commands can now be used to fully install RadiUID as an alternative to the Installation/Maintenance Utility
    - `request auto-complete` runs the script to install and activate the BASH Auto-Completion feature
    - `request freeradius-install` installs the FreeRADIUS app using the proper package manager
    - `request xml-update` downloads and installs an update to the xml.etree.ElementTree Python module. This upgrades ElementTree to 1.3.0, which is the minimum version required for RadiUID to run properly. This is only required when running Python 2.6.X.
    - `request reinstall keep-config` It reinstalls the RadiUID binary, BASH Auto-Completion feature, and RadiUID service, then restarts the service. The current configuration file is untouched to maintain settings during the upgrade. This command is now the recommended method for updating an existing RadiUID installation.
    - `request reinstall replace-config`performs all the tasks listed above with the exception that it also replaces the existing configuration (if one exists) with the default config. This command can be used to do a quick net-new installation of RadiUID without using the classic installer.
    - `request uninstall keep-config` completely removes RadiUID from the system (stops and disables the service, removes the binary, service file, and bash completion) but preserves the configuration directory at `/etc/radiuid/` for potential future reinstallation.
    - `request uninstall remove-config` performs a complete uninstallation including removal of all configuration files at `/etc/radiuid/`.

**BUG FIXES:**

- *ISSUE #16*: Newer builds of urllib2 in Python 2.7 started generating an error when the SSL certificate was invalid. Some logic has been added to detect when to use the proper SSL handling

- *ISSUE #17*: The RadiUID XML assembler was hard set to allow up to 100 UIDs in a single API call before splitting into multiple calls, which was overwhelming to the Palo Alto. That setting has been moved down to 50 UIDs per call and the setting `maxuidspercall` has been moved to the internal settings area near the top of the radiuid.py file.
    - This fix was reproduced and verified fixed by having RadiUID eat a FreeRADIUS Accounting log file with 2000 UIDs and push them into a test firewall. 50 UIDs per API call seems to work even with long usernames (50 characters).


--------------------------------------
### UPDATES IN V2.1.0 --> V2.2.0

**ADDED FEATURES:**

- The Munge Engine: RadiUID now includes a built-in rule-based string processor. The Munge Engine allows users to create a list of rules which will be used by RadiUID to filter, dissect, and reassemble User-IDs as they pass through the RadiUID service. More details on this feature can be found in the [Munge Engine](#the-munge-engine) section.

**BUG FIXES:**

- *ISSUE #19*: The `userdomain` configuration element now allows the use of the value `none` to specify that no domain should be prepended to User-IDs.


--------------------------------------
### UPDATES IN V2.2.0 --> V2.2.1

**BUG FIXES:**

- *ISSUE #20*: Added the `no-confirm` switch to the end of the commands `request reinstall keep-config`, `request reinstall replace-config`, `request freeradius-install` commands.


--------------------------------------
### UPDATES IN V2.2.1 --> V2.3.0

**ADDED FEATURES:**

- *ISSUE #21*: RadiUID is now available as a Docker image on [Docker Hub][docker-hub]. Small code changes were made to allow RadiUID to recognize when it is being run in a container and to be able to stop, start, and restart services while the container is running.


--------------------------------------
### UPDATES IN V2.3.0 --> V2.3.1

**BUG FIXES:**

- *ISSUE #22*: Repaired broken RadiUID service control when in a container. Now you can start, stop, and restart FreeRADIUS and RadiUID services from within the container without having to restart the container from the host.


--------------------------------------
### UPDATES IN V2.3.1 --> V2.3.2

**BUG FIXES:**

- *ISSUE #23*: Was unable to specify complex usernames (with periods, forward-slashes, domain-names, etc.) in the `radiuid push <pan> <username> <ip>` command due to strict username input checking. Removed input checking on username to allow any input in command.


--------------------------------------
### UPDATES IN V2.3.2 --> V2.4.0

**ADDED FEATURES:**

- Configurable TLS Protocol (#27): The TLS protocol used to communicate with the target firewalls can now be set to use TLS1.0 (previously the default), TLS1.1, or TLS1.2. This feature is configured with the `radiuid set tlsversion` command.

- Configurable RADIUS Stop Action (#26): RadiUID can now be configured to take different actions when a RADIUS stop log is found. It can continue to `push` the UID mapping (previous default action), it can `ignore` the UID mapping and discard it from the push, or it can take action on it and actively `clear` it from the firewall mapping table. This feature is configured with the `radiuid set radiusstopaction` command.

- Configurable Loop Time (#25): RadiUID would previously wait 10 seconds before each check of the RADIUS logs. This wait time is now configurable using the `radiuid set looptime` command.

**BUG FIXES:**

- *ISSUE #28*: Any configuration command which would generate a 1-line XML configuration change (example: `radiuid set maxloglines 10`) would not properly display the changed XML configuration item due to a bug in the `formatxml` library (used by `show_config_item`). This should now work properly.

**DEFAULT BEHAVIOR CHANGES:**
With the exposure of the `tlsversion` and `radiusstopaction` elements to configuration, best-practices have also been set for those values. The legacy behaviors are also supported and configurable if desired.

- Version 2.4.0 changes the default HTTPS TLS version from TLS1.0 to TLS1.2. This behavior can be changed back to pre-2.4.0 behavior using the command: `radiuid set tlsversion 1.0`.

- Version 2.4.0 changes the default RADIUS stop action (`radiusstopaction`) behavior from `push` to `clear` as a best practice. This more closely matches the commonly desired effect of synchronizing the PAN UID table with RADIUS logs. This behavior can be changed back to pre-2.4.0 behavior using the command: `radiuid set radiusstopaction push`.


--------------------------------------
### UPDATES IN V2.4.0 --> V2.4.1

**BUG FIXES:**

- *ISSUE #29*: Munge rule processing results within `push_uids` were being assembled back into `modipanduserdict` incorrectly formatted excluding the `status` field in the dictionary. The behavior seen was an exception thrown when RadiUID was run with munge rules configured and accounting logs available. This issue was reported by Marcus Cooke on the PacketPushers RadiUID blog post.


--------------------------------------
### UPDATES IN V2.4.1 --> V2.4.2

**BUG FIXES:**

- *ISSUE #30*: Munge discard overridden by an acceptance step in following rule. This was due to a bug in the munge engine, which did not properly break rule processing when a discard is detected. This issue was reported by Marcus Cooke on the PacketPushers RadiUID blog post.


--------------------------------------
### UPDATES IN V2.4.2 --> V2.4.3

**BUG FIXES:**

- *ISSUE #31*: RADIUS can [on occasion] report a RADIUS status type other than the standard `start`, `stop`, and `update`. A bug in RadiUID would cause the service to crash when this was seen due to an issue in the log reader. Adam reported this issue on the RadiUID GitHub issues list.


--------------------------------------
### UPDATES IN V2.4.3 --> V2.5.0

**ADDED FEATURES:**

- *ISSUE #36*: Added the ability to configure a custom port on a target using the `radiuid set target <target_id> port <port_number>` syntax.

- *ISSUE #37*: Added a feature to copy files from the FreeRADIUS log folder before deleting them. Can be configured with the `set acctlogcopypath <directory path>` syntax. Files with the same name are appended instead of copied.

**BUG FIXES:**

- *ISSUE #32*: Apostrophes in a username will cause a crash of the RadiUID process due to the method of string processing. The processing method has been changed to repair this issue.

- *OTHER*: FreeRADIUS not being installed when RadiUID gets installed with the wizard and is reset before completion. Fixed now.

- *OTHER*: Removed PAN-OS version awareness since there are no differences between major versions in API calls.


--------------------------------------
### UPDATES IN V2.5.0 --> V3.0.0

*Maintained by Brian Griffith*

**MAJOR CHANGES:**

- **Python 3 Compatibility**: Complete port from Python 2.7 to Python 3.8+
  - Updated shebang from `#!/usr/bin/python` to `#!/usr/bin/env python3`
  - Replaced `urllib2` with `urllib.request`, `urllib.error`, and `urllib.parse`
  - Replaced `commands` module with `subprocess`
  - Converted all `print` statements to `print()` functions
  - Replaced `raw_input()` with `input()`
  - Changed `.iteritems()` to `.items()` for dictionary iteration
  - Replaced deprecated `platform.dist()` with `platform.platform()`

- **Modular Package Structure**: Complete refactoring from a monolithic script to clean Python package
  - Organized into logical modules: `core/`, `cli/`, `ui/`, `firewall/`, `installer/`
  - Type hints throughout for better IDE support and code clarity
  - Proper dependency injection patterns
  - Can be installed via pip: `pip install .`

**NEW FEATURES:**

- **NPS/Windows Log Support**: Auto-detection and parsing of Windows NPS log formats
  - NPS XML format with `<Event>` tags
  - NPS/IAS CSV format
  - Automatic format detection based on file content

- **Live Log Processing**: Process continuously written log files without file deletion
  - Position tracking for efficient incremental processing
  - Automatic detection of log rotation/truncation
  - Configure with `set livelog` commands

- **Network Mount Dependencies**: Configure RadiUID service to wait for network mounts
  - Systemd service integration with mount units
  - Configure during installation or with `request set-mount`
  - Automatic prompt when setting `radiuslogpath` to network location

- **Installation Improvements**:
  - Python 3.8+ version check during installation
  - Prefers `dnf` over `yum` for package management
  - Network mount configuration prompt during wizard

- **Modern Python Packaging**:
  - `pyproject.toml` for pip installation
  - pytest test suite
  - GitHub Actions CI/CD
  - Pre-commit hooks for code quality

**NOTES:**

- This is a breaking change – Python 2.7 is no longer supported
- Minimum Python version: 3.8
- All command examples now use `python3` instead of `python`
- Single external dependency: PyYAML (for YAML configuration support)
- Thoroughly test in your environment before deploying to production


--------------------------------------
## UPGRADE PROCESSES

**Upgrading from v2.5.0 to v3.0.0:**

1. **Ensure Python 3 is installed**: Check with `python3 --version` (requires Python 3.x)
2. Perform a `radiuid show config set` command and save the `set` commands displayed in a safe place (just in case)
3. Download the code from the GitHub repo by using `git clone https://github.com/ghBrianG/radiuid.git`
    - If the "radiuid" folder already exists, you can use git to update the clone `cd radiuid/; git pull`
4. Move to the radiuid folder created by git using the `cd radiuid/` command
5. Change to the latest branch using the command `git checkout v3.0.0`
6. Perform a quick reinstall/update of RadiUID using the command `python3 radiuid.py request reinstall keep-config`
7. Type in CONFIRM and hit ENTER to confirm you want to perform the reinstallation
8. Once the installer exits, you should run `radiuid show config set` and see your configuration from before.
9. Check that you are running the new version by issuing `radiuid version`
10. Perform a `radiuid service all restart` command to restart RadiUID to use the new app version
	- *NOTE: The RadiUID service will continue running in the background throughout the installation/upgrade process. It is not until you restart/stop the service that the new version and configuration will take effect.*
11. You may also want to log out of the shell and back in to activate any new auto-complete functions.

**Upgrading from v2.X to v2.5.0:**

1. Perform a `radiuid show config set` command and save the `set` commands displayed in a safe place (just in case)
2. Download the code from the GitHub repo by using `git clone https://github.com/PackeTsar/radiuid.git`
    - If the "radiuid" folder already exists, you can use git to update the clone `cd radiuid/; git pull`
3. Move to the radiuid folder created by git using the `cd radiuid/` command
4. Change to the latest branch using the command `git checkout v2.5.0`
5. Perform a quick reinstall/update of RadiUID using the command `python3 radiuid.py request reinstall keep-config`
6. Type in CONFIRM and hit ENTER to confirm you want to perform the reinstallation
7. Once the installer exits, you should run `radiuid show config set` and see your configuration from before.
8. Check that you are running the new version by issuing `radiuid version`
9. Perform a `radiuid service all restart` command to restart RadiUID to use the new app version
	- *NOTE: The RadiUID service will continue running in the background throughout the installation/upgrade process. It is not until you restart/stop the service that the new version and configuration will take effect.*
10. You may also want to log out of the shell and back in to activate any new auto-complete functions.

**Upgrading from v1.X to v2.X.X:**

1. Change the name of your config file (/etc/radiuid/radiuid.yaml) by issuing the command
   `mv /etc/radiuid/radiuid.yaml /etc/radiuid/radiuid.yaml.backup`
2. Grab the contents to have them handy during the installation of the new version `more /etc/radiuid/radiuid.yaml.backup`
3. Download the v2.X.X code from the GitHub repo by using `git clone https://github.com/PackeTsar/radiuid.git`
    - If the "radiuid" folder already exists, you may want to use git to update the clone `cd radiuid/; git pull`
4. Move to the radiuid folder created by git using the `cd radiuid/` command
5. Perform a full installation of RadiUID using the command `python3 radiuid.py install`
6. Follow the prompts and fill out the appropriate information using the information from the old configuration file
7. Once the installer exits, you should run `radiuid show config set` and see your configuration.
8. Perform a `radiuid service all restart` command to restart RadiUID to use the new app version


--------------------------------------
## DOCKERFILES

These are the Dockerfile scripts to build RadiUID v3.0.0 Docker images. These use Rocky Linux (the community successor
to CentOS) as the base image.

> **Note:** The pre-built images on [Docker Hub][docker-hub] are from the original project and only support v2.5.0. Use
> these Dockerfiles to build v3.0.0 images.

**With SSH**

```dockerfile
FROM rockylinux:9
LABEL maintainer="Brian Griffith"

### Install Python 3 and dependencies ###
RUN dnf install -y python3 python3-pip curl tar

### Install and configure SSH Server for SSH access to container ###
RUN dnf install -y openssh openssh-server openssh-clients sudo passwd
RUN ssh-keygen -A
RUN sed -i "s/UsePAM.*/UsePAM yes/g" /etc/ssh/sshd_config
RUN useradd admin -G wheel -s /bin/bash -m
RUN echo 'root:radiuid' | chpasswd
RUN echo '%wheel ALL=(ALL) ALL' >> /etc/sudoers

### Download and install RadiUID v3.0.0 ###
RUN curl -sL https://codeload.github.com/ghBrianG/radiuid/tar.gz/v3.0.0 | tar xz
RUN pip3 install pyyaml
RUN cd radiuid-3.0.0 && python3 radiuid.py request reinstall replace-config no-confirm
RUN cd radiuid-3.0.0 && python3 radiuid.py request freeradius-install no-confirm

### Expose ports and provide run commands ###
EXPOSE 1813/udp
EXPOSE 1813/tcp
EXPOSE 22/tcp
CMD /usr/sbin/sshd && radiusd && radiuid run
```

**Without SSH**

```dockerfile
FROM rockylinux:9
LABEL maintainer="Brian Griffith"

### Install Python 3 and dependencies ###
RUN dnf install -y python3 python3-pip curl tar

### Download and install RadiUID v3.0.0 ###
RUN curl -sL https://codeload.github.com/ghBrianG/radiuid/tar.gz/v3.0.0 | tar xz
RUN pip3 install pyyaml
RUN cd radiuid-3.0.0 && python3 radiuid.py request reinstall replace-config no-confirm
RUN cd radiuid-3.0.0 && python3 radiuid.py request freeradius-install no-confirm

### Expose ports and provide run commands ###
EXPOSE 1813/udp
EXPOSE 1813/tcp
CMD radiusd && radiuid run
```

**Docker Build**

To build your own Docker image:

1. Install Docker on your system (`dnf install docker` or `apt install docker.io`) and start it (
   `systemctl start docker`)
2. Create a new file called `Dockerfile`: `vi Dockerfile`
3. Paste in the text from one of the above scripts, save, and exit (`:wq`)
4. Build the Docker image: `docker build -t radiuid:3.0.0 .`
5. Run the `docker images` command to verify the image was created
6. To run the image: `docker run -it -p 1813:1813/udp -p 1813:1813/tcp --name radiuid -t radiuid:3.0.0`
    - Add `-p 222:22/tcp` if using the SSH version
7. You will enter interactive mode where you can run `radiuid` commands. Press CTRL+P then CTRL+Q to detach while
   leaving the container running.
8. If using the SSH Dockerfile, connect via SSH to port 222 on the Docker host
9. To push to a registry:
   `docker tag radiuid:3.0.0 yourregistry/radiuid:3.0.0 && docker push yourregistry/radiuid:3.0.0`


--------------------------------------
## CONTRIBUTING

If you would like to help out by contributing code or reporting issues, please do!

Visit the GitHub page (https://github.com/ghBrianG/radiuid) and either report an issue or fork the project, commit some changes, and submit a pull request.

**Original Project:** This is a fork of the original RadiUID project by John W Kerns (PackeTsar): https://github.com/PackeTsar/radiuid

[logo]: /radiuid-logo-tiny-100.png
[docker-hub]: https://hub.docker.com/r/packetsar/
[centos-post-install]: https://github.com/PackeTsar/scriptfury/blob/master/CentOS_Post_Install.md
[ubuntu-post-install]: https://github.com/PackeTsar/scriptfury/blob/master/Ubuntu_Post_Install.md
