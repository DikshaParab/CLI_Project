from github import Github
from getpass import getpass
from utils import print_error, print_success

def authenticate_github():
    """Authenticate with GitHub using personal access token"""
    while True:
        try:
            token = getpass("Enter your GitHub personal access token: ")
            if not token:
                raise ValueError("Token cannot be empty")
                
            github = Github(token)
            user = github.get_user()
            print_success(f"Authenticated as {user.login}")
            return github
            
        except Exception as e:
            print_error(f"Authentication failed: {str(e)}")
            if input("Try again? (y/n): ").lower() != 'y':
                raise SystemExit("Exiting...")