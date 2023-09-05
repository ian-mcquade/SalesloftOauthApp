
# Salesloft Record Upsert Automation Tool

This is a Flask application that automates the process of upserting accounts and contacts in Salesloft via CSV uploads. It is currently used to update the crm_id with the corresponding Salesforce id to link the records as part of an integration between Salesloft and Salesforce.

## Features

- OAuth2 Authorization with Salesloft
- Upsert Salesloft accounts via CSV upload
- Upsert Salesloft contacts via CSV upload
- Real-time progress tracking
- Automatic token refresh

## Pre-requisites

- Python 3.x
- Flask
- `requests` library
- `python-dotenv`

## Setup and Installation

1. **Clone the repository**

    ```bash
    git clone [https://github.com/ian-mcquade/SalesloftOauthApp.git]
    ```


2. **Setup Environment Variables**

    Create a `.env` file in your project directory and add your Salesloft credentials.

    ```env
    c_id=YOUR_CLIENT_ID
    c_secret=YOUR_CLIENT_SECRET
    s_key=YOUR_SECRET_KEY
    ```

5. **Run the application**

    ```bash
    python oauth_app.py
    ```

## Usage

1. **Authorize Salesloft Account**

    Navigate to `http://localhost:8000/` and click on "Authorize Salesloft" to perform the OAuth2 authorization and login with your Salesloft credentials

2. **Upsert Salesloft Accounts**

    After authorization, you'll be redirected to a page with a link to upload your CSV file for accounts. 

3. **Upsert Salesloft Contacts**

    Similar to accounts, you'll also see a link to upload your CSV file for contacts.

## CSV Format

The expected CSV format for accounts and contacts should have the following columns:

### For Accounts

- `id`: The Salesloft ID of the account
- `crm_id`: The CRM ID of the account (Salesforce ID)

### For Contacts

- `id`: The Salesloft ID of the contact
- `crm_id`: The CRM ID of the contact (Salesforce ID)

## Contributing

If you'd like to contribute, please fork the repository and use a feature branch. Pull requests are warmly welcome. Thanks!

---
