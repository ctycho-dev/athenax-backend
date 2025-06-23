import os
import jwt
from jwt import PyJWKClient
# import certifi
# print(certifi.where())

# # Force Python to use the updated certifi certificates
# os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
# os.environ["SSL_CERT_FILE"] = certifi.where()

jwks_url = 'https://auth.privy.io/api/v1/apps/cm95tgbm001lnkv0k83wsckd3/jwks.json'
appId = 'cm95tgbm001lnkv0k83wsckd3'


accessToken = """eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IlUtMGJ1Y3U0VjJEUkZoTTJRN1VERTZCYXlKWWpwTFJ4enFDZGlKNUFQN2sifQ.eyJzaWQiOiJjbTlneDB0eTAwMG4zbDQwbTRocGhsdHR1IiwiaXNzIjoicHJpdnkuaW8iLCJpYXQiOjE3NDQ3MTYyMjcsImF1ZCI6ImNtOTV0Z2JtMDAxbG5rdjBrODN3c2NrZDMiLCJzdWIiOiJkaWQ6cHJpdnk6Y205ZmxyYjZuMDBnY2xkMG11MWR5bnkwYyIsImV4cCI6MTc0NDcxOTgyN30.nu4KrimaVJfQWY38wmhdVxo24yFKGArRCyf06KOpd9F7cSXcynYkj6zriE5WdVIv25ZoVs4alIOx85bWpO1hDA"""

# Create a JWKS client to fetch the correct key
jwks_client = PyJWKClient(jwks_url)

try:
    # Get the correct public key based on the JWT's "kid" (Key ID)
    signing_key = jwks_client.get_signing_key_from_jwt(accessToken)
    
    # Decode and verify the JWT
    decoded = jwt.decode(
        accessToken,
        signing_key.key,
        issuer="privy.io",
        audience=appId,
        algorithms=["ES256"]
    )
    print("Token is valid! Decoded payload:", decoded)
except Exception as e:
    print("Token verification failed:", e)

