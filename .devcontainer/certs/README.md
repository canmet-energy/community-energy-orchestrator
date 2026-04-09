# Certificate Folder

## Purpose

This folder is for adding corporate SSL certificates when building Docker images in environments with SSL inspection (e.g., NRCan network).

## Usage

### Place Your Certificates Here

1. Obtain your corporate root CA certificates from your IT/security team
2. Copy them to this `.devcontainer/certs/` folder (`.crt` or `.pem` format)
3. Build the Docker image:
   ```bash
   docker compose build api
   ```

**Build output will show:**
```
✅ Certificates: Secure validation OK (with custom certificates)
```

If no certificates are provided:
```
⚠️ Certificates: Insecure mode (SSL verification disabled)
Please check your custom certificates...
```

The build automatically:
- Validates certificate files
- Installs them into the container
- Tests network connectivity
- Configures all tools (curl, uv, pip, npm, etc.) appropriately

## How It Works

The build uses the `certctl-safe.sh` script (from the bluesky project) which:
1. Validates certificate format
2. Installs certificates to system trust store
3. Probes network connectivity
4. Automatically configures environment variables for secure/insecure mode
5. Shows clear status messages during build

## Security Note

**Do NOT commit certificate files to git.**

Certificates should be:
- Obtained from your IT/security team
- Placed locally in this folder
- Never pushed to public repositories

## Certificate Format

Accepted formats:
- `.crt` (PEM-encoded certificate)
- `.pem` (PEM-encoded certificate)

Files should contain CA root certificates in PEM format.
