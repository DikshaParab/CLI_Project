import time
import os
import json
import stat
import bcrypt
from github import Github
from getpass import getpass
from utils import print_error, print_success, print_warning, print_info, display_header
from rich.console import Console
from rich.table import Table
from rich import box

AUTH_FILE = ".gh_auth.json"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(stored_hash: str, provided_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            provided_password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )
    except Exception:
        return False

def save_credentials(username: str, token: str, password: str) -> bool:
    temp_path = None  
    try:
        credentials = {
            "username": username,
            "token": token,
            "password_hash": hash_password(password)
        }

        data = {"users": []}
        
        if os.path.exists(AUTH_FILE):
            try:
                with open(AUTH_FILE, "r") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, dict) and "users" in existing_data:
                        data = existing_data
            except json.JSONDecodeError:
                pass

        updated = False
        for i, user in enumerate(data["users"]):
            if user["username"] == username:
                data["users"][i] = credentials
                updated = True
                break
        
        if not updated:
            data["users"].append(credentials)

        temp_path = f"{AUTH_FILE}.tmp"
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=4)

        os.chmod(temp_path, stat.S_IRUSR | stat.S_IWUSR)
        
        if os.path.exists(AUTH_FILE):
            os.remove(AUTH_FILE)
        os.rename(temp_path, AUTH_FILE)

        return True
        
    except Exception as e:
        print_error(f"Failed to save credentials: {str(e)}")
        # Clean up temp file if it exists
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def load_credentials(username: str, password: str) -> str:
    try:
        if not os.path.exists(AUTH_FILE):
            print_warning("No credentials file found")
            return None

        with open(AUTH_FILE, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "users" not in data:
            print_error("Invalid credentials format")
            return None

        for user in data["users"]:
            if user.get("username") == username:
                if verify_password(user.get("password_hash", ""), password):
                    return user.get("token")
                else:
                    print_warning("Invalid password")
                    return None

        print_warning("Username not found")
        return None
    except json.JSONDecodeError:
        print_error("Credentials file is corrupted")
        return None
    except Exception as e:
        print_error(f"Error loading credentials: {str(e)}")
        return None

def authenticate_github() -> dict:
    console = Console()
    session_data = {
        'github': None,
        'last_activity': time.time(),
        'authenticated': False
    }
    
    while True:
        display_header("\nGitHub Authentication")

        has_credentials = os.path.exists(AUTH_FILE) and os.path.getsize(AUTH_FILE) > 0
        
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Option", style="cyan")
        table.add_column("Description", style="white")

        if has_credentials:
            table.add_row("1", "Login with existing credentials")
            table.add_row("2", "Add new user")
        else:
            table.add_row("1", "Add first user")
        table.add_row("x", "[red]Exit[/red]")

        console.print(table)

        choice = input("\nSelect an option: ").strip().lower()

        if choice == 'x':
            print_success("\nGoodbye!\n")
            raise SystemExit(0)
        elif choice == '1' and has_credentials:
            gh = handle_existing_user()
            if gh:
                session_data['github'] = gh
                session_data['authenticated'] = True
                return session_data
        elif choice in ('1', '2'):
            gh = handle_new_user()
            if gh:
                session_data['github'] = gh
                session_data['authenticated'] = True
                return session_data
        else:
            print_warning("Invalid choice, please try again")
            
def handle_existing_user() -> Github:
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        try:
            display_header("\nExisting User Login")
            
            username = input("Enter your username: ").strip()
            password = getpass("Enter your password: ")
            
            token = load_credentials(username, password)
            if not token:
                raise ValueError("Invalid credentials")
            
            gh = Github(token)
            user = gh.get_user()
            if not hasattr(user, 'login'):
                raise ValueError("Invalid GitHub response")
            
            print_success(f"Welcome back {user.login}!")
            return gh
            
        except Exception as e:
            attempts += 1
            remaining = max_attempts - attempts
            print_error(f"\nLogin failed: {str(e)}")
            if remaining > 0:
                print_warning(f"{remaining} attempt(s) remaining")
                if input("Try again? (y/n): ").lower() != 'y':
                    break
            else:
                print_error("Maximum attempts reached")
                input("Press Enter to continue...")
    
    return None

def handle_new_user() -> Github:
    display_header("New GitHub Login")
    
    try:
        print_info("\nYou'll need a GitHub personal access token with repo scope")
        print_info("Create one at: https://github.com/settings/tokens/new\n")
        
        username = input("Enter your username: ").strip()
        token = getpass("Enter yourGitHub personal access token: ")
        
        gh = Github(token)
        user = gh.get_user()
        if not hasattr(user, 'login'):
            raise ValueError("Invalid GitHub token")
        
        print_success(f"\nSuccessfully connected as {user.login}")
        
        while True:
            password = getpass("\nSet a decryption password: ")
            if not password:
                print_error("Password cannot be empty!")
                continue
                
            confirm = getpass("Confirm password: ")
            if password == confirm:
                break
            print_error("Passwords don't match!")
        
        if save_credentials(username, token, password):
            print_success("\nCredentials saved securely!")
            return gh
        else:
            raise Exception("Failed to save credentials")
        
    except Exception as e:
        print_error(f"\nRegistration failed: {str(e)}")
        input("Press Enter to continue...")
        return None