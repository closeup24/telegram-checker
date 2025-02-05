import asyncio
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # For Python 3.9+ (if using an earlier version, use pytz)
from typing import List, Tuple, Any
from telethon import TelegramClient, types
from telethon.errors.rpcerrorlist import MsgIdInvalidError
from tqdm import tqdm


class TelegramChecker:
    def __init__(self, api_id: int, api_hash: str, groups: List[str], keywords: List[str],
                 time_filter: int = 0) -> None:
        """
        :param api_id: API ID for Telethon.
        :param api_hash: API Hash for Telethon.
        :param groups: List of groups (public usernames or group IDs).
        :param keywords: List of keywords for filtering.
        :param time_filter: Number of hours for filtering posts. If 0, then for today.
        """
        self.api_id: int = api_id
        self.api_hash: str = api_hash
        self.groups: List[str] = groups
        self.keywords: List[str] = keywords
        self.time_filter: int = time_filter  # if 0, filter by today's date
        self.tz: ZoneInfo = ZoneInfo("Europe/Kyiv")

    @staticmethod
    def highlight_keywords(text: str, keywords: List[str]) -> str:
        """
        Highlights found keywords using an HTML <span> tag with a yellow background,
        black text color, and bold font.
        """
        pattern: re.Pattern = re.compile("|".join(re.escape(keyword) for keyword in keywords), re.IGNORECASE)

        def repl(match: re.Match) -> str:
            return f'<span style="background-color: yellow; color: black; font-weight: bold;">{match.group(0)}</span>'

        return pattern.sub(repl, text)

    def _get_time_filter(self) -> datetime:
        """
        Returns the threshold time for filtering messages.
        If time_filter == 0, returns the beginning of the current day (in Kyiv time),
        otherwise returns the current time minus N hours.
        """
        now: datetime = datetime.now(self.tz)
        if self.time_filter == 0:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            return now - timedelta(hours=self.time_filter)

    async def fetch_posts(self, client: TelegramClient) -> List[Tuple[Any, types.Message, str]]:
        """
        Fetches all top-level messages (posts) from all groups for the selected period.
        Returns a list of tuples (entity, post, group_username).
        """
        time_threshold: datetime = self._get_time_filter()
        posts: List[Tuple[Any, types.Message, str]] = []
        for group_username in self.groups:
            try:
                entity: Any = await client.get_entity(group_username)
                print(f"Processing group: {group_username}")
            except Exception as e:
                print(f"Failed to access group {group_username}: {e}")
                continue

            async for msg in client.iter_messages(entity):
                msg_time: datetime = msg.date.astimezone(self.tz)
                if msg_time < time_threshold:
                    break
                # Top-level message (not a reply)
                if msg.reply_to_msg_id is None:
                    posts.append((entity, msg, group_username))
        print(f"Found {len(posts)} posts for the specified period.")
        return posts

    def filter_posts_by_keywords(self, posts: List[Tuple[Any, types.Message, str]]) -> List[
        Tuple[Any, types.Message, str]]:
        """
        Filters posts to retain only those that contain at least one keyword.
        Returns a list of posts that meet the condition.
        """
        filtered: List[Tuple[Any, types.Message, str]] = []
        for entity, post, group_username in posts:
            if post.text and any(keyword.lower() in post.text.lower() for keyword in self.keywords):
                filtered.append((entity, post, group_username))
        return filtered

    def save_posts(self, posts: List[Tuple[Any, types.Message, str]]) -> None:
        """
        Saves the given list of posts to the Markdown file 'saved_posts.md'.
        """
        # Sort posts by date (from oldest to newest)
        posts.sort(key=lambda x: x[1].date)
        with open('saved_posts.md', 'w', encoding='utf-8') as f:
            for entity, post, group_username in posts:
                post_time: datetime = post.date.astimezone(self.tz)
                highlighted_text: str = self.highlight_keywords(post.text, self.keywords)
                if hasattr(entity, 'username') and entity.username:
                    post_link: str = f"https://t.me/{entity.username}/{post.id}"
                else:
                    post_link = "No public link"
                f.write(f"### Group: {group_username}\n")
                f.write(f"**Date:** {post_time.strftime('%Y-%m-%d %H:%M:%S')} (Kyiv)\n\n")
                f.write("**Post:**\n\n")
                f.write(f"{highlighted_text}\n\n")
                f.write(f"[Post Link]({post_link})\n\n")
                f.write("---\n\n")
        print(f"Saved {len(posts)} posts with keywords in 'saved_posts.md'.")

    async def fetch_comments(self, client: TelegramClient, posts: List[Tuple[Any, types.Message, str]]) -> List[
        Tuple[Any, types.Message, str, types.Message]]:
        """
        For each of the given posts, fetches all replies (comments).
        Returns a list of tuples (entity, comment, group_username, post) for comments
        that contain at least one keyword.
        """
        comments: List[Tuple[Any, types.Message, str, types.Message]] = []
        for entity, post, group_username in tqdm(posts, desc="Collecting comments"):
            # Skip if the post does not support comments
            if post.replies is None:
                continue
            try:
                async for reply in client.iter_messages(entity, reply_to=post.id):
                    comments.append((entity, reply, group_username, post))
            except MsgIdInvalidError as e:
                print(f"Skipping post {post.id} from group {group_username} due to error: {e}")
                continue

        # Filter comments by keywords
        filtered_comments: List[Tuple[Any, types.Message, str, types.Message]] = []
        for entity, reply, group_username, post in comments:
            if reply.text and any(keyword.lower() in reply.text.lower() for keyword in self.keywords):
                filtered_comments.append((entity, reply, group_username, post))
        print(f"Found {len(filtered_comments)} comments with keywords for posts in the specified period.")
        return filtered_comments

    def save_comments(self, comments: List[Tuple[Any, types.Message, str, types.Message]]) -> None:
        """
        Saves the given list of comments to the Markdown file 'saved_comments.md'.
        """
        # Sort comments by date (from oldest to newest)
        comments.sort(key=lambda x: x[1].date)
        with open('saved_comments.md', 'w', encoding='utf-8') as f:
            for entity, comment, group_username, post in comments:
                comment_time: datetime = comment.date.astimezone(self.tz)
                highlighted_text: str = self.highlight_keywords(comment.text, self.keywords)
                if hasattr(entity, 'username') and entity.username:
                    comment_link: str = f"https://t.me/{entity.username}/{post.id}?comment={comment.id}"
                else:
                    comment_link = "No public link"
                f.write(f"### Group: {group_username}\n")
                f.write(f"**Comment Date:** {comment_time.strftime('%Y-%m-%d %H:%M:%S')} (Kyiv)\n\n")
                f.write("**Comment:**\n\n")
                f.write(f"{highlighted_text}\n\n")
                f.write(f"[Comment Link]({comment_link})\n\n")
                f.write("---\n\n")
        print(f"Saved {len(comments)} comments with keywords in 'saved_comments.md'.")

    async def run(self) -> None:
        async with TelegramClient('session_name', self.api_id, self.api_hash) as client:
            # Fetch posts for the specified period
            all_posts: List[Tuple[Any, types.Message, str]] = await self.fetch_posts(client)
            # Filter posts by keywords for saving
            posts_with_keywords: List[Tuple[Any, types.Message, str]] = self.filter_posts_by_keywords(all_posts)
            self.save_posts(posts_with_keywords)
            # Fetch comments for all posts (even if the post does not contain keywords)ls -lag
            comments: List[Tuple[Any, types.Message, str, types.Message]] = await self.fetch_comments(client, all_posts)
            self.save_comments(comments)


if __name__ == '__main__':
    checker = TelegramChecker(
        api_id=0,
        api_hash='',
        groups=[],
        keywords=[],
        time_filter=0
    )
    asyncio.run(checker.run())
