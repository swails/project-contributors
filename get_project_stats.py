#!/usr/bin/env python

from typing import Dict, Optional
import requests
import typer
import re

app = typer.Typer()

SESSION = requests.Session()

def get_total_commits(base_url: str) -> int:
    commits_url = f"{base_url}/commits"

    response = SESSION.get(commits_url, params={"per_page": 1, "page": 1})

    total_commit_re = re.compile(r"[?&]page=(\d+)")
    pieces = response.headers["link"].split(",")
    for piece in pieces:
        if 'rel="last"' in piece:
            if rematch := total_commit_re.findall(piece):
                if len(rematch) != 1:
                    raise RuntimeError(f"Too many matches [{rematch}]!")
                return int(rematch[0])
            else:
                raise RuntimeError(f"Could not find total number of pages in response headers {response.headers}")
    else:
        raise RuntimeError("Could not find last page!")

@app.command()
def contributors(
    organization: str = typer.Argument(..., help="The GitHub organization owning the repository"),
    repository: str = typer.Argument(..., help="The project to analyze results for."),
    num_contributors: int = typer.Option(100000, "-n", "--num-contributors", help="Number of contributors"),
    username: Optional[str] = typer.Option(None, "-u", "--username", envvar="GH_USERNAME"),
    pat: Optional[str] = typer.Option(None, "-p", "--pat", envvar="GH_TOKEN"),
) -> None:
    base_url = f"https://api.github.com/repos/{organization}/{repository}"

    if username is not None and pat is not None:
        SESSION.auth = (username, pat)

    requested_contributors: Dict[str, int] = dict()

    contributors_url = f"{base_url}/contributors"
    total_commits = get_total_commits(base_url)

    current_page = 1
    while len(requested_contributors) < num_contributors:
        response = SESSION.get(contributors_url, params={"page": current_page})
        if not response.json():
            break
        for contributor in response.json():
            requested_contributors[contributor["login"]] = contributor["contributions"]
            if len(requested_contributors) >= num_contributors:
                break

        current_page += 1

    running_total_commits = 0
    typer.echo(typer.style(f"Total commits: {total_commits}", bold=True))
    typer.echo("")
    max_size = max(len(x) for x in requested_contributors)
    typer.echo(f"{{:<{max_size}}} {'# commits':<15s} % cmt % tot".format("Contributor"))
    typer.echo("-" * (max_size + 28))
    for contributor, count in requested_contributors.items():
        typer.echo(f"{{:<{max_size}}} {count:15d} {count / total_commits * 100: 5.1f} {(running_total_commits + count) / total_commits * 100: 5.1f}".format(contributor))
        running_total_commits += count

if __name__ == "__main__":
    app()
