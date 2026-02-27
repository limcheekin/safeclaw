import jwt
import datetime
import argparse
import sys
import os

def generate_token(private_key_path: str, days_valid: int = 365) -> str:
    """Generates a JWT signed with the provided RSA private key."""
    if not os.path.exists(private_key_path):
        print(f"Error: Private key file '{private_key_path}' not found.", file=sys.stderr)
        sys.exit(1)
        
    with open(private_key_path, 'r') as f:
        private_key = f.read()

    # Define the payload
    # sub: Subject of the token (who the token refers to)
    # iat: Issued at
    # exp: Expiration time
    payload = {
        "sub": "localai",
        "iat": datetime.datetime.now(datetime.timezone.utc),
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days_valid)
    }

    try:
        # Encode using the private key and RS256 algorithm
        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token
    except Exception as e:
        print(f"Error generating token: {e}", file=sys.stderr)
        print("Hint: Ensure the key is a valid RSA private key and 'cryptography' is installed.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a JWT token for SafeClaw MCP authentication.")
    parser.add_argument("--key", default="private.pem", help="Path to the private key file (default: private.pem)")
    parser.add_argument("--days", type=int, default=365, help="Number of days until the token expires (default: 365)")
    
    args = parser.parse_args()
    
    print(f"Generating token using key: {args.key}, valid for {args.days} days...\n")
    
    token = generate_token(args.key, args.days)
    
    print("Generated JWT Token:")
    print("-" * 60)
    print(token)
    print("-" * 60)
    print(f"\nThis token will expire in {args.days} days.")
    print("Use this token as <YOUR_GENERATED_JWT_TOKEN> in your LocalAI configuration.")
