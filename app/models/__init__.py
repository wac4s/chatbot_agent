from app.routes import (
    User,
    Video,
    Photo,
    Comment,
    Hashtag,
    Notification,
    Report,
    # association tables
    follows_table,
    blocked_users,
    likes,
    photo_likes,
    photo_hashtag_association,
    video_hashtag_association,
)

__all__ = [
    "User",
    "Video",
    "Photo",
    "Comment",
    "Hashtag",
    "Notification",
    "Report",
    "follows_table",
    "blocked_users",
    "likes",
    "photo_likes",
    "photo_hashtag_association",
    "video_hashtag_association",
]