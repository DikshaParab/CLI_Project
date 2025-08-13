import os
import time
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress
from github_auth import authenticate_github
from repo_browser import TEXT_EXTENSIONS, fetch_user_repos, display_repo_tree, index_repository
from chroma_integration import ChromaManager
from utils import (print_success, print_error, print_warning, display_header)

class RepoManagerCLI:
    def __init__(self):
        self.console = Console()
        self.chroma = ChromaManager()
        self.github = None
        self.repos = []
        self.user = None
        self.session = None  
    
    def run(self):
        try:
            while True:
                self.session = authenticate_github()
                if not self.session or not self.session['authenticated']:
                    break
                    
                self.github = self.session['github']
                self.user = self.github.get_user()
                self.main_menu()
                self._clear_session()

        except KeyboardInterrupt:
            print_error("\nOperation cancelled by user")
        except Exception as e:
            print_error(f"Fatal error: {str(e)}")
        finally:
            input("\nPress Enter to exit...")

    def check_session(self):
        if not self.session or not self.session['authenticated']:
            return False
        
        if time.time() - self.session['last_activity'] > 8 * 3600:
            print_warning("\nSession expired due to inactivity")
            return False
            
        self.session['last_activity'] = time.time()  
        return True

    def main_menu(self):
        display_header(f"\nWelcome {self.user.login}")
        while self.check_session():  
            display_header("\nMain Menu")
            
            menu_table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
            menu_table.add_column("Option", style="cyan", width=5)
            menu_table.add_column("Description", style="white")
            
            menu_items = [
                ("1", "List my repositories"),
                ("2", "View repository structure"),
                ("3", "Index repository"),
                ("4", "Basic text search"),
                ("5", "Semantic search"),
                ("6", "[yellow]Logout[/yellow]"),
                ("7", "[red]Exit[/red]")
            ]
            
            for item in menu_items:
                menu_table.add_row(*item)
            
            self.console.print(menu_table)
            
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
                self.logout()
                return  
            elif choice == "7":
                print_success("\nGoodbye!\n")
                raise SystemExit(0)
            else:
                print_warning("Invalid choice, please try again")

    def logout(self):
        print_success(f"\nLogged out {self.user.login} successfully!")
        self.session['authenticated'] = False
        self.session['github'] = None
        self.github = None
        self.user = None
        self.repos = []
                
    def list_repositories(self):
        display_header("\nMy Repositories")
        
        self.repos = fetch_user_repos(self.github)
        if not self.repos:
            print_warning("No repositories found")
            return
        
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Repository", style="bold green" , width=60)
        
        for idx, repo in enumerate(self.repos, 1):
            table.add_row(
                str(idx),
                repo.name
            )
        
        self.console.print(table)
    
    def view_repository_structure(self):
        try:
            if not self.repos:
                self.repos = fetch_user_repos(self.github)
            
            repo_idx = self._select_repository("Select repository to view")
            if repo_idx is None:  
                return
            
            repo = self.repos[repo_idx]
            display_header(f"\nRepository Structure: {repo.name}")
            
            try:
                tree = display_repo_tree(repo)
                self.console.print(tree)
            except Exception as e:
                print_error(f"Failed to display repository structure: {str(e)}")
                input("\nPress Enter to return to menu...")
                return
                
        except Exception as e:
            print_error(f"Unexpected error: {str(e)}")
            input("\nPress Enter to return to menu...")
            return
    
    def _search_repo_contents(self, repo, query):
        matches = []
        
        def search_contents(contents, path=""):
            try:
                for content in contents:
                    if content.type == "dir":
                        search_contents(repo.get_contents(content.path), content.path)
                    else:
                        _, ext = os.path.splitext(content.path)
                        if ext.lower() in TEXT_EXTENSIONS:
                            try:
                                file_content = content.decoded_content.decode('utf-8')
                                if query.lower() in file_content.lower():
                                    lines = file_content.split('\n')
                                    matching_lines = [
                                        f"Line {i+1}: {line.strip()}" 
                                        for i, line in enumerate(lines) 
                                        if query.lower() in line.lower()
                                    ]
                                    preview = "\n".join(matching_lines[:3])  
                                    matches.append((content.path, preview))
                            except UnicodeDecodeError:
                                continue
            except Exception as e:
                print_warning(f"Error searching {path}: {str(e)}")
        
        try:
            search_contents(repo.get_contents(""))
            return matches
        except Exception as e:
            print_warning(f"Error accessing repository {repo.name}: {str(e)}")
            return []

    def index_repository(self):
        try:
            if not self.repos:
                self.repos = fetch_user_repos(self.github)
            
            repo_idx = self._select_repository("Select repository to index")
            if repo_idx is None: 
                return
            
            repo = self.repos[repo_idx]
            display_header(f"\nIndexing Repository: {repo.name}")
            
            try:
                success = index_repository(repo, self.chroma)
                if success:
                    print_success(f"Successfully indexed repository: {repo.name}")
                else:
                    print_warning(f"Indexing completed with issues for: {repo.name}")
            except Exception as e:
                print_error(f"Failed to index repository: {str(e)}")
                
        except Exception as e:
            print_error(f"Unexpected error during indexing: {str(e)}")
        finally:
            input("\nPress Enter to return to menu...")

    def _display_search_results_table(self, results, search_type="Basic"):
        table = Table(
            title=f"{search_type} Search Results",
            box=box.ROUNDED,
            header_style="bold magenta",
            show_lines=True
        )
        
        table.add_column("#", style="cyan", width=4)
        table.add_column("Repository", style="green", width=25)
        table.add_column("File Path", width=40)
        table.add_column("Preview", width=60)
        
        for idx, (repo_name, file_path, preview) in enumerate(results, 1):
            table.add_row(
                str(idx),
                repo_name,
                file_path,
                preview
            )
        
        self.console.print(table)

    def _get_preview_count(self):
        while True:
            try:
                count = input("\nNumber of results to display (default 5): ").strip()
                if not count:
                    return 5
                count = int(count)
                if count > 0:
                    return count
                print_warning("Please enter a positive number")
            except ValueError:
                print_warning("Please enter a valid number")

    def search_all_repositories_basic(self):
        if not self.repos:
            self.repos = fetch_user_repos(self.github)
        
        display_header("\nGitHub Repository Manager - Basic Text Search")
        query = input("Enter search query: ").strip().lower()
        if not query:
            print_warning("Please enter a search query")
            return
        
        preview_count = self._get_preview_count()
        found_results = False
        all_results = []
        
        with Progress() as progress:
            task = progress.add_task("Searching all repositories...", total=len(self.repos))
            
            for repo in self.repos:
                progress.update(task, advance=1, description=f"Searching {repo.name[:20]}...")
                
                try:
                    matches = self._search_repo_contents(repo, query)
                    if matches:
                        found_results = True
                        for path, preview in matches[:preview_count]:  
                            all_results.append((
                                repo.name,
                                path,
                                f"{preview[:200]}{'...' if len(preview) > 200 else ''}"
                            ))
                except Exception as e:
                    print_warning(f"Error searching {repo.name}: {str(e)}")
                    continue
        
        if found_results:
            self._display_search_results_table(all_results, "Basic Text")
        else:
            print_warning("\nNo matches found in any repository")

    def search_indexed_repositories(self):
        indexed_repos = self.chroma.list_indexed_repos()
        if not indexed_repos:
            print_warning("No indexed repositories found. Please index repositories first.")
            return
        
        display_header("\nGitHub Repository Manager - Semantic Search")
        query = input("Enter search query: ").strip()
        if not query:
            print_warning("Please enter a search query")
            return
        
        preview_count = self._get_preview_count()
        results = self.chroma.search_all(query, n_results=preview_count)
        
        if not results:
            print_warning("No results found in any indexed repository")
            return
        
        all_results = []
        for repo_name, result in results.items():
            for doc, meta in zip(result['documents'][0], result['metadatas'][0]):
                all_results.append((
                    repo_name,
                    meta['path'],
                    f"{doc[:200]}{'...' if len(doc) > 200 else ''}"
                ))
        
        self._display_search_results_table(all_results, "Semantic")

    def _select_repository(self, prompt):
        if not self.repos:
            print_warning("No repositories available")
            return None
        
        print("\nAvailable repositories:")
        for idx, repo in enumerate(self.repos, 1):
            print(f"{idx}. {repo.name} {'(private)' if repo.private else ''}")
        
        try:
            choice = input(f"\n{prompt} (1-{len(self.repos)}, 'b' to back): ").strip().lower()
            if choice == 'b':
                return None
                
            choice = int(choice) - 1
            if 0 <= choice < len(self.repos):
                return choice
            print_warning(f"Please enter a number between 1 and {len(self.repos)}")
        except ValueError:
            print_warning("Please enter a valid number")
        
        return None

def main():
    try:
        cli = RepoManagerCLI()
        cli.run()
    except Exception as e:
        print_error(f"Application error: {str(e)}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()