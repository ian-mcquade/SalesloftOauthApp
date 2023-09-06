from flask import Flask, redirect, request, session, url_for, jsonify
import requests
import csv
import io
import time
import os
from dotenv import load_dotenv 

load_dotenv()


my_secret_key = os.environ.get('s_key')


app = Flask(__name__)
app.secret_key = my_secret_key 

@app.route('/')
def index():
    return '<a href="/authorize_salesloft">Authorize Salesloft</a>'

@app.route('/authorize_salesloft')
def authorize_salesloft():
    client_id = os.environ.get('c_id')
    redirect_uri = 'http://localhost:8000/callback'
    authorization_url = f"https://accounts.salesloft.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    context = request.args.get('context')
    scope = request.args.get('scope')
    token_data = get_tokens(code, context, scope)
    print("Access Token:", token_data['access_token'])
    print("Refresh Token:", token_data['refresh_token'])
    print('Scope:',scope)
    session['access_token'] = token_data['access_token']
    session['refresh_token'] = token_data['refresh_token']
    return  (f'<a href="{url_for("account_upload_csv")}">Account CSV Upload</a></br>'
             f'<a href="{url_for("contact_upload_csv")}">Contact CSV Upload </a>')
        
            
def get_tokens(code, context, scope):
    token_url = "https://accounts.salesloft.com/oauth/token"
    payload = {
        "client_id": os.environ.get('c_id'),
        "client_secret": os.environ.get('c_secret'),
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/callback",
        "context": context,
        "scope": scope
    }
    response = requests.post(token_url, json=payload)
    return response.json()


def refresh_token():
    refresh_token_url = "https://accounts.salesloft.com/oauth/token"
    payload = {
        "client_id": os.environ.get('c_id'),
        "client_secret": os.environ.get('c_secret'),
        "grant_type": "refresh_token",
        "refresh_token": session['refresh_token']
    }
    response = requests.post(refresh_token_url, json=payload)
    token_data = response.json()
    session['access_token'] = token_data['access_token']
    session['refresh_token'] = token_data['refresh_token']

def api_request(url, payload):
    if 'access_token' not in session:
        raise Exception("No access token in session. Please authorize first.")
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 401: # Token has expired
        refresh_token()
        headers["Authorization"] = f"Bearer {session['access_token']}"
        response = requests.post(url, json=payload, headers=headers)

    return response
@app.route('/upsert_account', methods=['POST'])
def upsert_account():
    account_id = request.form['account_id']
    crm_id = request.form['crm_id']

    # Define the URL and payload for the upsert request
    url = "https://api.salesloft.com/v2/account_upserts"
    payload = {
        "upsert_key": "id",
        "id": account_id,
        "crm_id": crm_id,
        "crm_id_type": "salesforce"
    }


    # Make the API request
    response = api_request(url, payload)

    if response.status_code == 200:
        return f"Account with ID {account_id} upserted successfully.", 200
    else:
        return f"Failed to upsert account with ID {account_id}. Error: {response.text}", 400

@app.route('/upsert_form')
def upsert_form():
    return '''
    <form action="/upsert_account" method="post">
        Salesloft ID: <input type="text" name="account_id"><br>
        CRM ID: <input type="text" name="crm_id"><br>
        <input type="submit" value="Submit">
    </form>
    '''

@app.route('/account_upload_csv', methods=['GET', 'POST'])
def account_upload_csv():
   
    sf_ids = [] #list of Salesforce id's that will be returned that were succesfully updated
    new_line = '\n' # new line variable so that I can use in F strings
    errors = []
    
    if request.method == 'POST':
        csv_file = request.files['file']
        if not csv_file.filename.endswith('.csv'):
            return "Please upload a CSV file.", 400
        
        csv_content = csv_file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(csv_content))
        
        total_rows = sum(1 for _ in csv.DictReader(io.StringIO(csv_content))) # Calculate total rows before loop
        csv_data = csv.DictReader(io.StringIO(csv_content)) # Read the data again
        
        successful_upserts = 0  # Counter for successful upserts
        request_count = 0  # Counter to track API request counts
        
        for index, row in enumerate(csv_data):
            print(row) #used when I'm getting errors with CSV file
            account_id = row['\ufeffid'] # '\ufeffid' if the file has an encoding issue, 'id' if not
            crm_id = row['crm_id']
            
            # Define the URL and payload for the upsert request
            url = "https://api.salesloft.com/v2/account_upserts"
            payload = {
                "upsert_key": "id",
                "id": account_id,
                "crm_id": crm_id,
                "crm_id_type": "salesforce"
            }

            # Make the API request
            print(f"Upserting: ID {account_id} - CRM ID {crm_id}")

            response = api_request(url, payload)
            response_data = response.json()
            if response.status_code // 100 == 2: #check if response code is the 200's
                successful_upserts += 1  #increment upsert counter
                sf_ids.append(crm_id) # add successful account id's to list 
                

            else:
                error_message = f"Failed upsert for ID {account_id}. Response: {response.text}"
                print(error_message)
                errors.append(error_message)
            
            request_count += 1
            if request_count == 600:  # Check if we've hit the rate limit
                time.sleep(60)  # Sleep for 60 seconds
                request_count = 0  # Reset the counter
                
            session['progress'] = (index + 1) / total_rows * 100    
        
        response_message = []

        if successful_upserts:
            response_message.append(f"Accounts upserted successfully! Total: {successful_upserts}")
            response_message.append(f"List of SFDC ids: {new_line} {new_line.join(map(str, sf_ids))}")

        if errors:
            response_message.append("Some accounts failed to upsert:")
            response_message.extend(errors)

        return f"<pre>{new_line.join(response_message)}</pre>", 200 if not errors else 400

    return '''
    <form action="/account_upload_csv" method="post" enctype="multipart/form-data">
        Upload your CSV: <input type="file" name="file"><br>
        <input type="submit" value="Upload and Process">
        <progress id="progressBar" max="100" value="0"></progress>
    <div id="status">0% complete</div>
    <script>
    function updateProgress() {
        fetch('/progress')
            .then(response => response.json())
            .then(data => {
                document.getElementById('progressBar').value = data.progress;
                document.getElementById('status').innerText = `${data.progress.toFixed(2)}% complete`;
                if (data.progress < 100) {
                    setTimeout(updateProgress, 1000);  // check every second
                } else {
                    document.getElementById('status').innerText = 'Processing complete!';
                }
            });
    }

    document.querySelector('form').addEventListener('submit', function() {
        updateProgress(); // Start updating progress when the form is submitted
    });
</script>
    </form>
    
    ''' 
    
@app.route('/contact_upload_csv', methods=['GET', 'POST'])
def contact_upload_csv():
         
    sf_ids = [] #list of Salesforce id's that will be returned that were succesfully updated
    new_line = '\n' # new line variable so that I can use in F strings
    errors = []
    
    if request.method == 'POST':
        csv_file = request.files['file']
        if not csv_file.filename.endswith('.csv'):
            return "Please upload a CSV file.", 400

        csv_content = csv_file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(csv_content))
        
        total_rows = sum(1 for _ in csv.DictReader(io.StringIO(csv_content))) # Calculate total rows before loop
        csv_data = csv.DictReader(io.StringIO(csv_content)) # Read the data again
        
        successful_upserts = 0  # Counter for successful upserts
        request_count = 0  # Counter to track API request counts
        
        for index, row in enumerate(csv_data):
            person_id = row['id']
            crm_id = row['crm_id']
            
            # Define the URL and payload for the upsert request
            url = f"https://api.salesloft.com/v2/person_upserts"
            payload = {
                "upsert_key": "id",
                "id": person_id,
                "crm_id": crm_id,
                "crm_id_type": "salesforce"
            }

            # Make the API request
            print(f"Upserting: ID {person_id} - CRM ID {crm_id}")

            
            response = api_request(url, payload)
            #response_data = response.json()
            if response.status_code // 100 == 2: #check if response code is the 200's
                successful_upserts += 1  #increment upsert counter
                sf_ids.append(crm_id) # add successful account id's to list 
                

            else:
                error_message = f"Failed update for ID {person_id}. Response: {response.text}"
                print(error_message)
                errors.append(error_message)
            
            request_count += 1
            if request_count == 600:  # Check if we've hit the rate limit
                time.sleep(60)  # Sleep for 60 seconds
                request_count = 0  # Reset the counter
                
            session['progress'] = (index + 1) / total_rows * 100     
        
        response_message = []

        if successful_upserts:
            response_message.append(f"People updated successfully! Total: {successful_upserts}")
            response_message.append(f"List of SFDC ids: {new_line} {new_line.join(map(str, sf_ids))}")

        if errors:
            response_message.append("Some contacts failed to upsert:")
            response_message.extend(errors)

        return f"<pre>{new_line.join(response_message)}</pre>", 200 if not errors else 400

    return '''
    <form action="/contact_upload_csv" method="post" enctype="multipart/form-data">
        Upload your CSV: <input type="file" name="file"><br>
        <input type="submit" value="Upload and Process">
        <progress id="progressBar" max="100" value="0"></progress>
    <div id="status">0% complete</div>
    <script>
    function updateProgress() {
        fetch('/progress')
            .then(response => response.json())
            .then(data => {
                document.getElementById('progressBar').value = data.progress;
                document.getElementById('status').innerText = `${data.progress.toFixed(2)}% complete`;
                if (data.progress < 100) {
                    setTimeout(updateProgress, 1000);  // check every second
                } else {
                    document.getElementById('status').innerText = 'Processing complete!';
                }
            });
    }

    document.querySelector('form').addEventListener('submit', function() {
        updateProgress(); // Start updating progress when the form is submitted
    });
</script>
    </form>
    
    '''    

@app.route('/progress')
def progress():
    return jsonify(progress=session.get('progress', 0))

if __name__ == '__main__':
    app.run(port=8000, debug=True)
    
    


