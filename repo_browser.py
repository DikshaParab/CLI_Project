from github import GithubException
from rich.table import Table
from rich.tree import Tree
from rich import box
from rich.progress import Progress
import os
from rich.console import Console
from rich import box
from datetime import datetime
from utils import print_error, print_info, print_success, print_warning

TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.rst', '.json', '.yaml', '.yml', '.html', '.css', '.js',
    '.java', '.c', '.cpp', '.h', '.sh', '.go'  }

def fetch_user_repos(github, descending=True):
    try:
        user = github.get_user()
        repos = list(user.get_repos())            
        return sorted(repos, key=lambda r: r.name.lower(), reverse=not descending)
    except GithubException as e:
        print_error(f"Failed to fetch repositories: {str(e)}")
        return []
    except Exception as e:
        print_error(f"Unexpected error fetching repositories: {str(e)}")
        return []

def display_repos_table(repos, title="My Repositories"):
    if not repos:
        print_info("No repositories found")
        return

    try:
        console = Console()
        
        table = Table(
            title=title,
            box=box.ROUNDED,
            header_style="bold magenta",
            title_style="bold cyan",
            show_lines=False
        )
        
        table.add_column("#", style="cyan", width=4)
        table.add_column("Name", style="green", width=20)

        for idx, repo in enumerate(repos, 1):
            table.add_row(str(idx), repo.name)
        
        console.print(table)
    except Exception as e:
        print_error(f"Failed to display repositories table: {str(e)}")
        raise 

def display_repo_tree(repo):
    try:
        tree = Tree(f"[bold]{repo.name}")
        
        def build_tree(node, path=""):
            try:
                contents = repo.get_contents(path)
                for content in contents:
                    if content.type == "dir":
                        branch = node.add(f"[yellow]{content.name}")
                        build_tree(branch, content.path)
                    else:
                        node.add(f"[cyan]{content.name}")
            except GithubException as e:
                node.add(f"[red]Error loading {path}: {str(e)}")
            except Exception as e:
                node.add(f"[red]Unexpected error: {str(e)}")
        
        build_tree(tree)
        return tree
        
    except Exception as e:
        print_error(f"Failed to generate repository tree: {str(e)}")
        error_tree = Tree(f"[red]Error displaying {repo.name}")
        error_tree.add(f"[yellow]{str(e)}")
        return error_tree

def index_repository(repo, chroma_manager):
    try:
        print_info(f"Indexing repository: {repo.name}")
        
        documents = []
        metadatas = []
        ids = []
        error_count = 0
        
        def process_contents(contents, path=""):
            nonlocal error_count
            try:
                for content in contents:
                    try:
                        if content.type == "dir":
                            process_contents(repo.get_contents(content.path), content.path)
                        else:
                            _, ext = os.path.splitext(content.path)
                            if ext.lower() in TEXT_EXTENSIONS:
                                try:
                                    file_content = content.decoded_content.decode('utf-8')
                                    documents.append(file_content)
                                    metadatas.append({
                                        "path": content.path,
                                        "repo": repo.name,
                                        "type": "file",
                                        "extension": ext
                                    })
                                    ids.append(f"{repo.name}_{content.path}")
                                except UnicodeDecodeError:
                                    print_warning(f"Skipping binary file: {content.path}")
                                except Exception as e:
                                    print_warning(f"Error processing {content.path}: {str(e)}")
                                    error_count += 1
                    except GithubException as e:
                        print_warning(f"Error accessing {content.path if hasattr(content, 'path') else path}: {str(e)}")
                        error_count += 1
            except Exception as e:
                print_error(f"Error processing directory {path}: {str(e)}")
                error_count += 1
        
        with Progress() as progress:
            task = progress.add_task(f"Indexing {repo.name}...", total=1)
            try:
                process_contents(repo.get_contents(""))
            except Exception as e:
                print_error(f"Failed to access repository contents: {str(e)}")
                return False
            progress.update(task, completed=1)
        
        if documents:
            try:
                chroma_manager.store_documents(repo.name, documents, metadatas, ids)
                print_success(f"Indexed {len(documents)} files from {repo.name}")
                if error_count > 0:
                    print_warning(f"Encountered {error_count} errors during indexing")
                return True
            except Exception as e:
                print_error(f"Failed to store documents in ChromaDB: {str(e)}")
                return False
        else:
            print_warning(f"No indexable files found in {repo.name}")
            return False
            
    except Exception as e:
        print_error(f"Unexpected error during indexing: {str(e)}")
        return False