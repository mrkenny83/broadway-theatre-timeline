# Broadway Theatre Timeline

Interactive 41-theatre Gantt chart powered by Broadway Now & Next. Open `index.html` via GitHub Pages. A scheduled GitHub Actions workflow checks the source every day at 11:23 UTC, validates the data, commits updates and deploys directly to Pages. It may fail if the source blocks automated requests or changes page structure; existing data is retained.

## Enable hosting

In the repository select **Settings → Pages → Source: GitHub Actions**. Then open **Actions → Refresh and publish Broadway timeline → Run workflow**. Your site URL is https://mrkenny83.github.io/broadway-theatre-timeline/.

## Publishing

The GitHub Actions Pages deployment runs after changes to `main` and on the daily scheduled refresh. If needed, select **Actions → Refresh and publish Broadway timeline → Run workflow** to publish manually. Hosting is provided by GitHub Pages.
