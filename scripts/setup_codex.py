"""Install the pinned repository-local Superpowers plugin."""
import subprocess


def main():
    for args in (['plugin', 'marketplace', 'add', '.', '--json'],
                 ['plugin', 'add', 'superpowers@c2s-tools', '--json']):
        subprocess.run(['node_modules/.bin/codex', *args], check=True)


if __name__ == '__main__': main()
