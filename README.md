#   <img src="https://www.softfire.eu/wp-content/uploads/SoftFIRE_Logo_Fireball-300x300.png" width="120"/>

  Copyright © 2016-2018 [SoftFIRE](https://www.softfire.eu/) and [TU Berlin](http://www.av.tu-berlin.de/next_generation_networks/).
  Licensed under [Apache v2 License](http://www.apache.org/licenses/LICENSE-2.0).

# UE Manager
The UE manager works underneath the [Physical Device Manager](https://github.com/softfire-eu/physical-device-manager) to reserve UE(s) for experimenters and grant them remote access to the UE(s) through [TeamViewer](https://www.teamviewer.com). This requires a [TeamViewer corporate license](https://www.teamviewer.com/en/pricing/) with support for sufficient number of concurrent channels, according to the number of experimenters that will work concurrently.


## Technical Requirements

The UE Manager requires an Apache web server with Python 2.7 installed. Additionally, a number of Python dependencies should be installed using pip, as follows:

  * sudo pip install 'bottle==0.12.13'
  * sudo pip install 'requests==2.18.4'

## Installation and configuration

The UE manager needs to be installed and configured manually using the following steps:


**1. Create a TeamViewer script token:**

For the UE manager to be able to communicate with TeamViewer via its REST API, a TeamViewer script token needs to be created as follows:

   1.1. Log in to the master TeamViewer account and go to the "Edit Profile" section.

   1.2. Under the "Apps" tab, click "Create script token"
   
   1.3. Assign a *name* and *description* to the script token, and select the following levels of access:
   
   * **Account management**: No access
   * **User management**: View, create and edit users
   * **Session management**: Create, view and edit all sessions
   * **Group management**: Create, view, delete, edit and share groups
   * **Connection reporting**: No access
   * **Meetings**: No access
   * **Computers & Contacts**: View, add, edit and delete entries
   * **TeamViewer policies**: No access
   
   1.4. After clicking "Save", copy and paste the returned token string to the "access_token" field of the file `tv_access_token.json`.
   
   
**2. Create TeamViewer user accounts:**

To support multiple experimenters, the corresponding number of user TeamViewer accounts need to be created and added to the master TeamViewer account. This is done as follows:

   2.1. Go to the *User management* tab from the home page
   
   2.2. Click the "Add user" button
   
   2.3. Complete the *Name*, *E-Mail* and *Password* fields, leaving all other fields unchanged, then click the "Add user" button to create the user.
   
   
**3. Configure and store user account details in local database:**

Once user accounts are added to TeamViewer, certain groups in TeamViewer need to be created and shared with these user accounts, and the relevant information added to a locally maintained database. To simplify this process, a script has been created to configure everything automatically. 

**Beware: this script will delete all existing groups within your master TeamViewer account.**

To run the script, call the following command from Terminal:

```
sudo python SetupTeamViewer.py --configure users
```

In addition to configuring user accounts, the script will also create:

  * a random default user account password which is saved to `default_user_account_details.json`; 
  
  * a random default device password which is saved to `default_device_details.json`; and
  
  * a random API access token which is saved to `api_access_token.json`.

A confirmation message will be displayed when the script has finished running.


**4. Configure UEs and add to TeamViewer account:**

All UEs that are to be remotely controlled by experimenters will need to have installed on them the [TeamViewer Host](https://play.google.com/store/apps/details?id=com.teamviewer.host.market) Android application. Not all phones currently support remote control, only remote viewing; [this article](https://community.teamviewer.com/t5/Knowledge-Base/Supported-manufacturers-for-remotely-controlling-Android-devices/ta-p/4730) lists the Android phones that currently support remote control via TeamViewer.

After installing the TeamViewer Host on a UE, sign in to the master TeamViewer account from the app. Then log in to the master account from a PC to check that the device appears in the "Unassigned" group. If it isn't, check for the UE in the "All" group, and add it to the "Unassigned" group manually.


**5. Store TeamViewer device details in local database:**

After installing the TeamViewer Host app on all UEs to be controlled by experimenters, the device details need to be stored in the local database using the SetupTeamViewer.py script. To run the script, call the following command from Terminal:

```
sudo python SetupTeamViewer.py --configure devices
```

A confirmation message will be displayed when the script has finished running.


**6. Move files:**

Once TeamViewer has been configured, certain files will need to be moved or copied to specific locations:

   6.1. Move or copy the following files to the directory `/etc/softfire/uemanager/` (creating the directory if it doesn't already exist): 
   * `api_access_token.json`
   * `default_device_details.json`
   * `default_user_account_details.json`
   * `tv_access_token.json`
   
   6.2. Move or copy the following files to the web server's html directory, typically `/var/www/html/`:
   * `UeManager.py`
   * `uemanager.db` 

**7. Start the UE Manager:**

After carrying out all of the prior configuration steps, the UE Manager web service can be started by running the following command in Terminal from the location at which the files in step 6.2 were copied:
   
   ```
   screen -S UeManager -d -m python UeManager.py
   ```
   
**8. Configure SoftFIRE Physical Device Manager**

If using the UE Manager in conjunction with the SoftFIRE Physical Device Manager, this will need to be configured to talk to the UE Manager by editing the "surrey-ue" field of the [`physical_resources.json`](https://github.com/softfire-eu/physical-device-manager/blob/master/etc/physical-resources.json) file with the URL of the server on which the UE Manager is hosted, as well as the "secret" key, which is the API access token set in the file `/etc/softfire/uemanager/api_access_token.json`


## Issue tracker

Issues and bug reports should be posted to the GitHub Issue Tracker of this project.

For any queries, please contact the author of the UE Manager:

**Dr George Kamel**\
*g.kamel [at] surrey.ac.uk*

# What is SoftFIRE?

SoftFIRE provides a set of technologies for building a federated experimental platform aimed at the construction and experimentation of services and functionalities built on top of NFV and SDN technologies.
The platform is a loose federation of already existing testbed owned and operated by distinct organizations for purposes of research and development.

SoftFIRE has three main objectives: supporting interoperability, programming and security of the federated testbed.
Supporting the programmability of the platform is then a major goal and it is the focus of the SoftFIRE’s Second Open Call.

## Licensing and distribution
Copyright © [2016-2018] SoftFIRE project

Licensed under the Apache License, Version 2.0 (the "License");

you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.