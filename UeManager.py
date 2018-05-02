from bottle import Bottle, run, request, route, post, delete, get, ServerAdapter
import io, string, json
import requests
import sqlite3
import random


## DEFINE MAIN VARIABLES
password_length = 16
db_connected = False
db_path = 'uemanager.db'
tv_access_token_path = '/etc/softfire/uemanager/tv_access_token.json'
api_access_token_path = '/etc/softfire/uemanager/api_access_token.json'
default_device_details_path = '/etc/softfire/uemanager/default_device_details.json'
default_user_account_path = '/etc/softfire/uemanager/default_user_account_details.json'
get_users_url = 'https://webapi.teamviewer.com/api/v1/users'
create_user_url = 'https://webapi.teamviewer.com/api/v1/users'
get_groups_url = 'https://webapi.teamviewer.com/api/v1/groups'
create_group_url = 'https://webapi.teamviewer.com/api/v1/groups'
share_group_url = 'https://webapi.teamviewer.com/api/v1/groups/<gID>/share_group'
get_devices_url = 'https://webapi.teamviewer.com/api/v1/devices'
share_device_url = 'https://webapi.teamviewer.com/api/v1/devices/<dID>'
get_sessions_url = 'https://webapi.teamviewer.com/api/v1/sessions'
mod_session_url = 'https://webapi.teamviewer.com/api/v1/sessions/<code>'
mod_user_url = 'https://webapi.teamviewer.com/api/v1/users/<uID>'


## INITIALISE APPLICATION

# Get TeamViewer script access token
with io.open(tv_access_token_path, 'r', encoding='utf-8') as tv_access_token_file:
    tv_access_token_data = json.load(tv_access_token_file)
    tv_access_token = tv_access_token_data["access_token"]
    
# Get API access token
with io.open(api_access_token_path, 'r', encoding='utf-8') as api_access_token_file:
    api_access_token_data = json.load(api_access_token_file)
    api_access_token = api_access_token_data["access_token"]
    
# Get default device details
with io.open(default_device_details_path, 'r', encoding='utf-8') as default_device_details_file:
    default_device_details_data = json.load(default_device_details_file)
    default_device_password = default_device_details_data["device_password"]
    default_device_groupid  = default_device_details_data["device_groupid"]
    
# Get default user account details
with io.open(default_user_account_path, 'r', encoding='utf-8') as default_user_account_file:
    default_user_account_data = json.load(default_user_account_file)
    default_user_account_password = default_user_account_data["user_password"]
    

# Create TeamViewer API session
s = requests.Session()
s.headers.update(
    {
        'Authorization': 'Bearer ' + tv_access_token,
        'Content-Type': 'application/json'
    }
)


## DEFINE FUNCTIONS

# copied from bottle. Only changes are to import ssl and wrap the socket
class SSLWSGIRefServer(ServerAdapter):
    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        import ssl
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.socket = ssl.wrap_socket (
         srv.socket,
         certfile='server.pem',  # path to certificate
         server_side=True)
        srv.serve_forever()

# Function to connect to main database
def db_connect():
    global db_connected
    try:
        # Connect to database
        db_conn = sqlite3.connect(db_path)
        db_connected = True
        return db_conn
    except Error as e:
        # To do: Send e-mail to admin to notify of error before returning from function
        db_connected = False
        return None
        
        
# Function to authorise http request to this application
def auth_request(req):
    # Check for 'Authorization' key in header
    if 'Authorization' in req.headers.keys():
        header = req.headers.get('Authorization').split(' ')
    else:
        auth_response = {
            'error' : 'no_access_token', 
            'error_description' : 'Access token is missing.', 
            'error_code' : '0'
        }
        return auth_response # return error
    
    # Check Authorization key contains Bearer and token
    if header[0]=='Bearer' and len(header)==2:
        access_token = header[1]
    else:
        auth_response = {
            'error' : 'invalid_token', 
            'error_description' : 'The access token provided is invalid.', 
            'error_code' : '1'
        }
        return auth_response # return error
    
    # Check validity of access token
    if access_token == api_access_token:
        auth_response = {
            'success' : 'token_valid'
        }
        return auth_response # return success
    else:
        error_response = {
            'error' : 'invalid_token', 
            'error_description' : 'The access token provided is invalid.', 
            'error_code' : '1'
        }
        return error_response # return error

        
## DEFINE ROUTE AND API CALLS

# Root path
@route('/')
def index():
    return '<h2>Restricted page.</h2>'
    

# Call to remove all UEs allocated to a specific user
@get('/test')
def test():
    return json.dumps({
        'status' : 'up'
    })


# Call to allocate a UE to a specific user
@post('/ue/reserve')
def reserve():
    result = list()
    
    # Authorize request
    response = auth_request(request)
    if 'error' in response:
        return json.dumps(response) # return error back to middleware

    # Connect to DB
    db_conn = db_connect()
    global db_connected
    if db_connected == 1:
        db_cursor = db_conn.cursor()
    else:
        # Could not connect to database - return appropriate error message
        error_response = {
            'error' : 'database_connection_error', 
            'error_description' : 'Could not connect to database.', 
            'error_code' : '2'
        }
        return json.dumps(error_response) # return error back to middleware
        
    # Check to see if there are available UEs...
    # Get devices with no assigned uID
    db_cursor.execute('''SELECT * FROM devices WHERE uID IS NULL or uID = ""''')
    device_lookup = db_cursor.fetchall()
    if len(device_lookup) == 0:
        # No UEs available to be assigned - return appropriate error message
        error_response = {
            'error' : 'no_free_ue', 
            'error_description' : 'There are no UEs available, as they are already in use by other experimenters.', 
            'error_code' : '7'
        }
        db_conn.close()
        return json.dumps(error_response) # return error back to middleware
        
    # Check if username already exists in database...
    # Get username
    username = request.json.get('username')
    resourceId = request.json.get('resourceId')
        
    # Get user records with given username from database
    db_cursor.execute('''SELECT * FROM users WHERE username = ?''', (username,))
    user_lookup = db_cursor.fetchall()
        
    # If user does not have any TeamViewer account associated with it, create password and store in DB together with username
    if len(user_lookup) == 0:
        # Get free accounts
        db_cursor.execute('''SELECT * FROM users WHERE username IS NULL or username = ""''')
        user_lookup = db_cursor.fetchall()
        
        # Get TV account details of the account to be assigned
        user_id = user_lookup[0][0]
        group_id = user_lookup[0][1]
        email = user_lookup[0][2]
        
        # Create cryptographically secure random password
        password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(password_length))
        
        # Update user table with new account assignment
        db_conn.execute('''UPDATE users SET username = ?, password = ? WHERE uID = ?''', (username, password, user_id))
        db_conn.commit()
    # Otherwise get the existing password of the user
    else:
        # Get TV account details of the assigned account
        user_id = user_lookup[0][0]
        group_id = user_lookup[0][1]
        email = user_lookup[0][2]
        password = user_lookup[0][4]
        
    # Call TeamViewer API to modify user account details (password)
    mod_user_url_custom = mod_user_url.replace('<uID>', 'u'+str(user_id)) # create custom API URL
    mod_user_response = s.put(
        mod_user_url_custom,
        json = {
            'password': password
        }
    )
        
    # Call TeamViewer API to add free device to user group
    free_device_id = device_lookup[0][0]
    free_device_name = device_lookup[0][2]
    share_device_url_custom = share_device_url.replace('<dID>', 'd'+str(free_device_id)) # create custom API URL
    share_device_response = s.put(
        share_device_url_custom,
        json = {
            'password': password,
            'groupid': 'g'+str(group_id)
        }
    )
    
    # Update device entry with new user id and resource id
    db_conn.execute('''UPDATE devices SET uID = ?, resourceId = ? WHERE dID = ?''', (user_id, resourceId, free_device_id))
    db_conn.commit()
    
    ## Get number of assigned devices from database
    #db_cursor.execute('''SELECT * FROM devices WHERE uID = ?''', (user_id,))
    #device_count_lookup = db_cursor.fetchall()
    #num_assigned_devices = len(device_count_lookup)
    
    # Return credentials back to user as implicit confirmation
    db_conn.close()
    
    result.append(json.dumps(
        {
            'url': 'https://login.teamviewer.com',
            'email': email, 
            'password' : password,
            'resource_id': resourceId,
            'ue_name': free_device_name
        }
    ))
    
    return result
    
# Call to remove all UEs allocated to a specific user
@delete('/ue/terminate')
def terminate():
    result = list()

    # Authorize request
    response = auth_request(request)
    if 'error' in response:
        return json.dumps(response) # return error back to middleware

    # Connect to DB
    db_conn = db_connect()
    global db_connected
    if db_connected:
        db_cursor = db_conn.cursor()
    else:
        # Could not connect to database - return appropriate error message
        error_response = {
            'error' : 'database_connection_error', 
            'error_description' : 'Could not connect to database.', 
            'error_code' : '2'
        }
        return error_response # return error back to middleware

    # Get username
    username = request.json.get('username')
    resourceId = request.json.get('resourceId')
    
    # Look up user
    db_cursor.execute('''SELECT * FROM users WHERE username = ?''', (username,))
    user_lookup = db_cursor.fetchall()
    
    # If user with given email address not found in database, return appropriate error message
    if len(user_lookup) == 0:
        error_response = {
            'error' : 'invalid_user', 
            'error_description' : 'User does not exist. No UEs to remove.', 
            'error_code' : '3'
        }
        db_conn.close()
        return error_response # return error back to middleware
    
    # Get user and group ids
    user_id = user_lookup[0][0]
    group_id = user_lookup[0][1]

    # Look up device id based on user id and resource id
    db_cursor.execute('''SELECT * FROM devices WHERE uID = ? AND resourceId = ?''', (user_id,resourceId,))
    device_lookup = db_cursor.fetchall()
    if len(device_lookup) == 0:
        error_response = {
            'error' : 'invalid_device', 
            'error_description' : 'Device does not exist.', 
            'error_code' : '8'
        }
        db_conn.close()
        return error_response # return error back to middleware
        
    device_id = device_lookup[0][0]

    # Terminate sessions of given device?

    # Move given device to 'Unassigned' group and assign default password
    share_device_url_custom = share_device_url.replace('<dID>', 'd'+str(device_id)) # create custom API URL
    share_device_response = s.put(
        share_device_url_custom,
        json = {
            'password': default_device_password,
            'groupid': 'g'+default_device_groupid
        }
    )

    # Remove uIDs in records of removed devices
    db_conn.execute('''UPDATE devices SET uID = NULL, resourceId = NULL WHERE dID = ?''', (device_id,))
    db_conn.commit()

    # Check if user has other devices in account
    # If no, reset password associated with account
    if len(device_lookup) == 1:
        mod_user_url_custom = mod_user_url.replace('<uID>', 'u'+str(user_id)) # create custom API URL
        mod_user_response = s.put(
            mod_user_url_custom,
            json = {
                'password': default_user_account_password
            }
        )
        
        # Remove usernames and passwords assigned to TV account in database
        db_conn.execute('''UPDATE users SET username = NULL, password = NULL WHERE uID = ?''', (user_id,))
        db_conn.commit()
        
    result.append(json.dumps(
        {
            'username' : username, 
            'assigned_devices' : '0'
        }
    ))

    return result
    

if __name__ == '__main__':
    run(host='0.0.0.0', port=8080, debug=False, reloader=False)
    #srv = SSLWSGIRefServer(host="0.0.0.0", port=8080)
    #run(server=srv)
