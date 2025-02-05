# Telegram Checker

Telegram Checker is a Python script that collects posts and comments from specified Telegram groups, filters them by keywords, and saves the results in Markdown files. The program uses the [Telethon](https://github.com/LonamiWebs/Telethon) library to interact with the Telegram API.

## Features

- **Post Collection** – The script fetches all top-level messages (posts) from the specified groups for a selected period (either for today or for the last N hours).
- **Keyword Filtering** – It filters posts and comments that contain at least one of the specified keywords.
- **Keyword Highlighting** – Detected keywords are highlighted using an HTML `<span>` tag with a yellow background, black text, and bold font.
- **Result Saving** – Filtered posts are saved in the `saved_posts.md` file, and filtered comments are saved in the `saved_comments.md` file.
