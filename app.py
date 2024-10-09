import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import shutil

app = Flask(__name__)
app.secret_key = '1a8f3ba5d2ef881f002227639e3a811ca349eca92a417e79'

os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# Cargar las credenciales desde client_secrets.json
CLIENT_SECRETS_FILE = "/home/updrivel/mysite/client_secrets.json"  # Cambiar si es necesario
SCOPES = ['https://www.googleapis.com/auth/drive.file']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authorize')
def authorize():
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=url_for('oauth2callback', _external=True)
        )
    except FileNotFoundError:
        return "Error: El archivo client_secrets.json no se encontró. Verifica la ruta y el nombre del archivo.", 500

    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    # Redirige a la página de carga después de la autenticación
    return redirect(url_for('upload_page'))

@app.route('/upload_page')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'credentials' not in session:
        return redirect('authorize')

    # Obtener los datos del formulario
    file_url = request.form['file_url']
    file_name = request.form['file_name']

    # Descargar el archivo
    download_file(file_url, file_name)

    # Subir el archivo a Google Drive
    credentials = Credentials(**session['credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_name, resumable=True)
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Eliminar el archivo descargado
    os.remove(file_name)

    return "Archivo subido a Google Drive con éxito!"

def download_file(url, file_name):
    response = requests.get(url, stream=True)
    with open(file_name, 'wb') as file:
        shutil.copyfileobj(response.raw, file)

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == '__main__':
    app.run(debug=True)
