# Ontology Marketplace Backend

FastAPI Server for serving the Ontology Marketplace API.

## Methodology

- Can be run as a single server or as multiple Google Cloud Run functions
- Calls are split into separate files, each able to be uploaded as individual Google Cloud Run functions
  - Auth is handled within each separate endpoint to support this

## Running as a single server

Using [uv](https://github.com/astral-sh/uv) for dependency management

```
uv sync
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Updating requirements.txt with uv

`requirements.txt` is generated from `pyproject.toml` using `uv`. After changing dependencies in `pyproject.toml`, regenerate the lock file with:

```bash
uv pip compile pyproject.toml -o requirements.txt
```

Optionally, to upgrade all pinned versions to the latest compatible releases:

```bash
uv pip compile --upgrade pyproject.toml -o requirements.txt
```

### Using Python 3.12 with uv (if `uv run python -V` shows 3.13)

If your environment or lock files were created with Python 3.13, recreate them for 3.12:

```bash
# Ensure Python 3.12 is available to uv
uv python install 3.12

# Remove any existing virtual environment
rm -rf .venv

# (Optional) regenerate lock/pins for 3.12
uv lock --python 3.12 || true
# Or, if using requirements.txt pins
uv pip compile --upgrade pyproject.toml -o requirements.txt

# Sync dependencies for Python 3.12
uv sync --python 3.12

# Verify the version uv will run
uv run --python 3.12 python -V
```

Interactive docs will then be available at http://localhost:8000/docs

Getting Firebase Auth Token to test in docs

```
API_KEY="<firebase_web_api_key>"
EMAIL="<user_email>"
PASSWORD="<user_password>"

ID_TOKEN=$(curl -s "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"returnSecureToken\":true}" \
  | jq -r '.idToken')

echo "ID Token: $ID_TOKEN"
```

In the interactive docs, click on the "Authorize" button. In the dialog box, enter in the ID_TOKEN directly in the value field (do not prefix with Bearer).

## Environment Variables

### Required for Firebase Authentication
- `GOOGLE_PROJECT_ID` (or `GOOGLE_CLOUD_PROJECT`, `GCP_PROJECT`, `FIREBASE_PROJECT_ID`, `PROJECT_ID`): Firebase project ID
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Stringified JSON of Firebase service account credentials

### Optional
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of allowed origins for CORS (default: "*")
  - Example: `"https://yourdomain.com,https://www.yourdomain.com,http://localhost:3000"`
  - Use `"*"` to allow all origins (not recommended for production)

### Local Development Testing

For local frontend testing without Firebase authentication, you can enable a development auth bypass:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. In your `.env` file, set:
   ```bash
   ALLOW_DEV_AUTH_BYPASS=1
   DEV_AUTH_EMAIL=your-email@example.com
   ```

3. When making HTTP requests from your frontend, include the `X-Dev-Email` header:
   ```javascript
   fetch('http://localhost:8000/search_ontologies', {
     headers: {
       'X-Dev-Email': 'your-email@example.com',
       'Content-Type': 'application/json'
     }
   })
   ```

Alternatively, if you set `DEV_AUTH_EMAIL` in the `.env` file, you don't need to include the header - the backend will automatically use that email.

**Note**: This bypass should NEVER be enabled in production!

## Deployment

### Recommended Hosting Services

This FastAPI app can be deployed to container-based hosting platforms. Here are three recommended options:

#### 1. **Google Cloud Run** (Recommended - Best for Firebase integration)

Since you're already using Firebase/Google Cloud services, Cloud Run offers seamless integration:

1. **Install gcloud CLI** (if not already installed):
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate and set project**:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Build and deploy**:
   ```bash
   # Build the container image
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ontology-marketplace-backend
   
   # Deploy to Cloud Run
   gcloud run deploy ontology-marketplace-backend \
     --image gcr.io/YOUR_PROJECT_ID/ontology-marketplace-backend \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars "GOOGLE_PROJECT_ID=YOUR_PROJECT_ID,GOOGLE_APPLICATION_CREDENTIALS_JSON=$(cat path/to/credentials.json | jq -c .)"
   ```

   **Note**: For `GOOGLE_APPLICATION_CREDENTIALS_JSON`, you can also set it in the Cloud Run console under "Variables & Secrets".

4. **Set CORS origins** (if needed):
   ```bash
   gcloud run services update ontology-marketplace-backend \
     --set-env-vars "CORS_ALLOWED_ORIGINS=https://yourdomain.com"
   ```

**Benefits**: Pay-per-request pricing, auto-scaling, integrated with Firebase/Google Cloud services

---

#### 2. **Railway** (Easiest Docker deployment)

Railway offers simple Docker-based deployment with a great developer experience:

1. **Sign up** at [railway.app](https://railway.app)

2. **Connect your GitHub repository** or deploy from CLI:
   ```bash
   # Install Railway CLI
   npm i -g @railway/cli
   
   # Login and initialize
   railway login
   railway init
   ```

3. **Set environment variables** in Railway dashboard:
   - `GOOGLE_PROJECT_ID`
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON` (paste full JSON string)
   - `CORS_ALLOWED_ORIGINS` (optional)

4. **Deploy**:
   ```bash
   railway up
   ```

Railway will automatically detect the Dockerfile and deploy. It provides a URL like `https://your-app.up.railway.app`

**Benefits**: Simple setup, automatic HTTPS, integrated monitoring, $5/month starter plan

---

#### 3. **Render** (Good free tier option)

Render offers free tier Docker hosting with easy deployment:

1. **Sign up** at [render.com](https://render.com)

2. **Create a new Web Service** and connect your GitHub repository

3. **Configure**:
   - **Build Command**: (leave empty, Render builds from Dockerfile)
   - **Start Command**: (leave empty, uses Dockerfile CMD)
   - **Environment**: `Docker`

4. **Set environment variables** in Render dashboard:
   - `GOOGLE_PROJECT_ID`: Your Firebase project ID
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`: **Important** - This must be a stringified JSON of your Firebase service account credentials. To get this:
     
     ```bash
     # Option 1: If you have the service account JSON file
     cat path/to/service-account-key.json | jq -c .
     
     # Option 2: Copy the entire JSON file content and minify it (remove all newlines/whitespace)
     # The entire JSON object should be on one line in the Render environment variable
     ```
     
     **Common mistake**: Don't set individual fields - paste the entire JSON object as a single-line string.
     
     Example format (all on one line):
     ```
     {"type":"service_account","project_id":"your-project-id","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}
     ```
   
   - `CORS_ALLOWED_ORIGINS` (optional): Comma-separated origins, e.g., `https://yourdomain.com,https://www.yourdomain.com`
   - `PORT` (optional - Render sets this automatically)

5. **Deploy**: Render will build and deploy automatically on git push

**Troubleshooting**: If you get `DefaultCredentialsError`, ensure `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set correctly:
- The value must be a valid JSON object (all on one line)
- Copy the entire JSON from your Firebase service account key file
- Make sure there are no extra quotes or escaping issues
- Verify `GOOGLE_PROJECT_ID` matches the project in your credentials

**Benefits**: Free tier available, automatic deployments, built-in SSL

---

### Local Docker Testing

Before deploying, test the Docker image locally:

```bash
# Build the image
docker build -t ontology-marketplace-backend:latest .

# Run locally
docker run --rm -p 8080:8080 \
  -e PORT=8080 \
  -e GOOGLE_PROJECT_ID="$GOOGLE_PROJECT_ID" \
  -e GOOGLE_APPLICATION_CREDENTIALS_JSON="$GOOGLE_APPLICATION_CREDENTIALS_JSON" \
  -e CORS_ALLOWED_ORIGINS="http://localhost:3000" \
  ontology-marketplace-backend:latest
```

The API will be available at `http://localhost:8080/docs`