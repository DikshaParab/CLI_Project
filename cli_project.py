import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from github_auth import authenticate_github
from repo_browser import fetch_user_repos, display_repo_tree, index_repository
from chroma_integration import ChromaManager
from utils import (
    print_success, print_error, print_info, print_warning,
    clear_screen, display_header
)

class RepoManagerCLI:
    def __init__(self):
        self.console = Console()
        self.chroma = ChromaManager()
        self.github = None
        self.repos = []
        self.user = None
    
    def run(self):
        display_header("GitHub Repository Manager")
        
        try:
            self.github = authenticate_github()
            self.user = self.github.get_user()
            self.main_menu()
        except KeyboardInterrupt:
            print_error("\nOperation cancelled by user")
        except Exception as e:
            print_error(f"Fatal error: {str(e)}")
    
    def main_menu(self):
        display_header(f"Welcome {self.user.login} to the GitHub Repository Manager CLI!")
        while True:
            display_header("Main Menu")
            
            print("1. List my repositories")
            print("2. View repository structure")
            print("3. Index repository")
            print("4. Search in all repositories (basic text search)")
            print("5. Search in indexed repositories (semantic search)")
            print("6. Exit")
            
            choice = input("\nSelect an option: ").strip()
            
            if choice == "1":
                self.list_repositories()
            elif choice == "2":
                self.view_repository_structure()
            elif choice == "3":
                self.index_repository()
            elif choice == "4":
                self.search_all_repositories_basic()
            elif choice == "5":
                self.search_indexed_repositories()
            elif choice == "6":
                print_success("\nGoodbye!\n")
                break
            else:
                print_warning("Invalid choice, please try again")
            
            input("\nPress Enter to continue...")
    
    def list_repositories(self):
        display_header("My Repositories")
        
        self.repos = fetch_user_repos(self.github)
        if not self.repos:
            print_warning("No repositories found")
            return
        
        for idx, repo in enumerate(self.repos, 1):
            print(f"{idx}. {repo.name}")
    
    def view_repository_structure(self):
        if not self.repos:
            self.repos = fetch_user_repos(self.github)
        
        repo_idx = self._select_repository("Select repository to view")
        if repo_idx is None:
            return
        
        repo = self.repos[repo_idx]
        display_header(f"Repository Structure: {repo.name}")
        
        tree = display_repo_tree(repo)
        self.console.print(tree)
    
    def index_repository(self):
        if not self.repos:
            self.repos = fetch_user_repos(self.github)
        
        repo_idx = self._select_repository("Select repository to index")
        if repo_idx is None:
            return
        
        repo = self.repos[repo_idx]
        index_repository(repo, self.chroma)
    
    def search_all_repositories_basic(self):
        if not self.repos:
            self.repos = fetch_user_repos(self.github)
        
        query = input("Enter search query: ").strip().lower()
        if not query:
            print_warning("Please enter a search query")
            return
        
        found_results = False
        
        with Progress() as progress:
            task = progress.add_task("Searching all repositories...", total=len(self.repos))
            
            for repo in self.repos:
                progress.update(task, advance=1, description=f"Searching {repo.name[:20]}...")
                
                try:
                    matches = self._search_repo_contents(repo, query)
                    if matches:
                        if not found_results:
                            print_success("\nSearch Results:")
                            found_results = True
                        print(f"\nRepository: {repo.name}")
                        for path, preview in matches:
                            print(f"  File: {path}")
                            print(f"  Preview: {preview[:200]}{'...' if len(preview) > 200 else ''}")
                            print("-" * 50)
                except Exception as e:
                    print_warning(f"Error searching {repo.name}: {str(e)}")
                    continue
        
        if not found_results:
            print_warning("\nNo matches found in any repository")

    def _search_repo_contents(self, repo, query):
        matches = []
        try:
            contents = repo.get_contents("")
            while contents:
                content = contents.pop(0)
                if content.type == "dir":
                    contents.extend(repo.get_contents(content.path))
                elif content.type == "file":
                    try:
                        file_content = content.decoded_content.decode('utf-8').lower()
                        if query in file_content:
                            preview = content.decoded_content.decode('utf-8')[:500]
                            matches.append((content.path, preview))
                    except UnicodeDecodeError:
                        continue  # Skip binary files
        except Exception as e:
            print_warning(f"Error processing {repo.name}: {str(e)}")
        return matches
    
    def search_indexed_repositories(self):
        indexed_repos = self.chroma.list_indexed_repos()
        if not indexed_repos:
            print_warning("No indexed repositories found. Please index repositories first.")
            return
        
        query = input("Enter search query: ").strip()
        if not query:
            print_warning("Please enter a search query")
            return
        
        results = self.chroma.search_all(query)
        
        if not results:
            print_warning("No results found in any indexed repository")
            return
        
        print_success("\nSemantic Search Results:")
        for repo_name, result in results.items():
            print(f"\nRepository: {repo_name}")
            for doc, meta in zip(result['documents'][0], result['metadatas'][0]):
                print(f"\nFile: {meta['path']}")
                print("-" * 50)
                print(doc[:500] + "..." if len(doc) > 500 else doc)
                print("-" * 50)
    
    def _select_repository(self, prompt):
        if not self.repos:
            print_warning("No repositories available")
            return None
        
        print("\nAvailable repositories:")
        for idx, repo in enumerate(self.repos, 1):
            print(f"{idx}. {repo.name}")
        
        try:
            choice = int(input(f"\n{prompt} (1-{len(self.repos)}): ")) - 1
            if 0 <= choice < len(self.repos):
                return choice
            print_warning("Invalid selection")
        except ValueError:
            print_warning("Please enter a valid number")
        
        return None

def main():
    cli = RepoManagerCLI()
    cli.run()

if __name__ == "__main__":
    main()