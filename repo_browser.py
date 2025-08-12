from github import GithubException
from rich.tree import Tree
from rich.progress import Progress
from utils import print_error, print_success, print_warning, print_info
from chroma_integration import ChromaManager
import os

TEXT_EXTENSIONS = {
    '.py', '.md', '.txt', '.rst', '.json', 
    '.yaml', '.yml', '.html', '.css', '.js'
}

def fetch_user_repos(github):
    try:
        user = github.get_user()
        return list(user.get_repos())
    except GithubException as e:
        print_error(f"Failed to fetch repositories: {str(e)}")
        return []

def display_repo_tree(repo):
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
        except GithubException:
            node.add("[red]Error loading contents")
    
    build_tree(tree)
    return tree

def index_repository(repo, chroma_manager):
    print_info(f"Indexing repository: {repo.name}")
    
    documents = []
    metadatas = []
    ids = []
    
    def process_contents(contents, path=""):
        for content in contents:
            if content.type == "dir":
                process_contents(repo.get_contents(content.path), content.path)
            else:
                try:
                    _, ext = os.path.splitext(content.path)
                    if ext.lower() in TEXT_EXTENSIONS:
                        file_content = content.decoded_content.decode('utf-8')
                        documents.append(file_content)
                        metadatas.append({
                            "path": content.path,
                            "repo": repo.name,
                            "type": "file"
                        })
                        ids.append(f"{repo.name}_{content.path}")
                except Exception:
                    continue
    
    with Progress() as progress:
        task = progress.add_task(f"Indexing {repo.name}...", total=1)
        process_contents(repo.get_contents(""))
        progress.update(task, completed=1)
    
    if documents:
        chroma_manager.store_documents(repo.name, documents, metadatas, ids)
        print_success(f"Indexed {len(documents)} files from {repo.name}")
    else:
        print_warning(f"No indexable files found in {repo.name}")