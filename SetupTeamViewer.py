import argparse
import io
import json
import requests
import sqlite3
import uuid


# Parameters
db_connected = False
db_path = 'uemanager.db'
tv_access_token_path = 'tv_access_token.json'
get_users_url = 'https://webapi.teamviewer.com/api/v1/users'
get_groups_url = 'https://webapi.teamviewer.com/api/v1/groups'
create_group_url = 'https://webapi.teamviewer.com/api/v1/groups'
delete_group_url = 'https://webapi.teamviewer.com/api/v1/groups/<gID>'
share_group_url = 'https://webapi.teamviewer.com/api/v1/groups/<gID>/share_group'
get_devices_url = 'https://webapi.teamviewer.com/api/v1/devices'


# Get TeamViewer script access token
with io.open(tv_access_token_path, 'r', encoding='utf-8') as tv_access_token_file:
    tv_access_token_data = json.load(tv_access_token_file)
    tv_access_token = tv_access_token_data["access_token"]
    
# Create TeamViewer API session
s = requests.Session()
s.headers.update(
    {
        'Authorization': 'Bearer ' + tv_access_token,
        'Content-Type': 'application/json'
    }
)

# Function to connect to main database
def db_connect():
    global db_connected
    try:
        db_conn = sqlite3.connect(db_path)
        db_connected = True
        return db_conn
    except Error as e:
        # To do: Send e-mail to admin to notify of error before returning from function
        db_connected = False
        return None


def populate_devices():
    # Connect to DB
    db_conn = db_connect()
    global db_connected
    if db_connected:
        db_cursor = db_conn.cursor()
    else:
        # Could not connect to database - return appropriate error message
        error_response = {
            'error': 'database_connection_error',
            'error_description': 'Could not connect to database.',
            'error_code': '2'
        }
        print error_response

    # Call TeamViewer API to query devices
    get_devices_response = s.get(get_devices_url)
        
    # Parse response
    get_devices_response_json = json.loads(get_devices_response.text)
        
    # Delete all entries in devices table in database
    db_cursor.execute('''DELETE FROM devices''')
        
    # Loop through devices and add to database
    for device in get_devices_response_json["devices"]:
        device_id = device['device_id'][1:] # remove 'd' prefix
        remotecontrol_id = device['remotecontrol_id'][1:] # remove 'r' prefix
        alias = device['alias']
        db_conn.execute('''INSERT INTO devices(dID, rID, name) VALUES(?, ?, ?)''', (device_id, remotecontrol_id, alias))
    
    db_conn.commit()
    db_conn.close()
    print "TeamViewer devices successfully saved."
    return


def populate_users():
    # Connect to DB
    db_conn = db_connect()
    global db_connected
    if db_connected:
        db_cursor = db_conn.cursor()
    else:
        # Could not connect to database - return appropriate error message
        error_response = {
            'error': 'database_connection_error',
            'error_description': 'Could not connect to database.',
            'error_code': '2'
        }
        print error_response
        return

    # Delete all existing groups in TeamViewer (except "Unassigned" group)
    get_groups_response = s.get(get_groups_url)
    get_groups_response_json = json.loads(get_groups_response.text)
    unassigned_group_exists = False
    unassigned_group_id = -1
    for group in get_groups_response_json["groups"]:
        group_id = group['id'][1:]
        group_name = group['name']
        if group_name != "Unassigned":
            delete_group_url_custom = delete_group_url.replace('<gID>', 'g' + str(group_id))  # create custom API URL
            s.delete(delete_group_url_custom)
            s.get(get_groups_url)
        else:
            unassigned_group_exists = True
            unassigned_group_id = group_id

    # If "Unassigned" group does not exist, create it...
    if not unassigned_group_exists:
        create_group_response = s.post(
            create_group_url,
            json={
                'name': "Unassigned"
            }
        )
        create_group_response_json = json.loads(create_group_response.text)
        unassigned_group_id = create_group_response_json['id'][1:]  # remove 'g' prefix

    # Set default device details
    default_device_details = {
        "device_password": str(uuid.uuid1().hex)[0:15],
        "device_groupid": unassigned_group_id
    }
    with open('default_device_details.json', 'w') as json_file:
        json.dump(default_device_details, json_file, indent=4)

    # Create random API access token for UE Manager
    api_access_token = {
        "access_token": str(uuid.uuid1()),
        "token_type": "bearer"
    }
    with open('api_access_token.json', 'w') as json_file:
        json.dump(api_access_token, json_file, indent=4)

    # Get all TeamViewer users and create and assign a group for each

    # Delete all entries in users table in database
    db_cursor.execute('''DELETE FROM users''')

    # Get existing users
    get_users_response = s.get(get_users_url, params={'permissions': 'ViewOwnConnections'})
    get_users_response_json = json.loads(get_users_response.text)
    user_count = 0

    # Loop through users and add to database
    for user in get_users_response_json["users"]:
        # Increment user count
        user_count += 1

        # Get user details
        user_id = user['id'][1:]  # remove 'u' prefix
        user_email = user['email']

        # Create new group for user
        create_group_response = s.post(
            create_group_url,
            json={
                'name': 'SoftFIRE UE Group ' + str(user_count)
            }
        )
        create_group_response_json = json.loads(create_group_response.text)
        group_id = create_group_response_json['id'][1:]  # remove 'g' prefix

        # Share group with user
        share_group_url_custom = share_group_url.replace('<gID>', 'g' + str(group_id))
        s.post(
            share_group_url_custom,
            json={
                'users': [
                    {
                        'userid': 'u' + str(user_id),
                        'permissions': 'read'
                    }
                ]
            }
        )

        # Insert new user and associated group into database
        db_conn.execute('''INSERT INTO users(uID, gID, email) VALUES(?, ?, ?)''', (user_id, group_id, user_email))
    
    db_conn.commit()
    db_conn.close()
    print "TeamViewer users successfully configured and saved."
    return


def main():
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--configure", type=str, default="", required=True,
                    help="CONFIGURE values are either 'users' or 'devices'")
    args = vars(ap.parse_args())

    # data for new API transaction
    # apiData is just dummy variables
    if args["configure"] == "users":
        populate_users()

    elif args["configure"] == "devices":
        populate_devices()

    else:
        print "Missing or invalid parameter."
        return
    

if __name__ == '__main__':
    main()

