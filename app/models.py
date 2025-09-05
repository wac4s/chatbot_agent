# models.py
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Table,
    ForeignKey,
    Text,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import relationship
from app.database import Base

# Association table for follow relationships
follows_table = Table(
    'follows',
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('users.id')),
    Column("following_id", Integer, ForeignKey("users.id")),
)

# Blocked users: user<->user (self-referential)
blocked_users = Table(
    "blocked_users",
    Base.metadata,
    Column("blocker_id", Integer, ForeignKey("users.id")),
    Column("blocked_id", Integer, ForeignKey("users.id")),
)

# Video likes: user<->video
likes = Table(
    "likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("video_id", Integer, ForeignKey("videos.id")),
)

# Photo likes: user<->photo
photo_likes = Table(
    "photo_likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("photo_id", Integer, ForeignKey("photos.id")),
)

# Hashtag associations
photo_hashtag_association = Table(
    "photo_hashtag_association",
    Base.metadata,
    Column("photo_id", Integer, ForeignKey("photos.id")),
    Column("hashtag_id", Integer, ForeignKey("hashtags.id")),
)

video_hashtag_association = Table(
    "video_hashtag_association",
    Base.metadata,
    Column("video_id", Integer, ForeignKey("videos.id")),
    Column("hashtag_id", Integer, ForeignKey("hashtags.id")),
)

# Models

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    bio = Column(String, nullable=True)
    avatar = Column(String, nullable=True)

    # Follows (self-referential many-to-many)
    followers = relationship(
        "User",
        secondary=follows_table,
        primaryjoin=id == follows_table.c.following_id,
        secondaryjoin=id == follows_table.c.follower_id,
        backref="following",
    )

    # Likes
    liked_videos = relationship("Video", secondary=likes, back_populates="liked_by")
    liked_photos = relationship("Photo", secondary=photo_likes, back_populates="liked_by")

    # Blocks (self-referential many-to-many)
    blocked = relationship(
        "User",
        secondary=blocked_users,
        primaryjoin=id == blocked_users.c.blocker_id,
        secondaryjoin=id == blocked_users.c.blocked_id,
        backref="blocked_by",
    )

class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    caption = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    # Add a timestamp for sorting by recency
    created_at = Column(DateTime, default=datetime.utcnow)

    liked_by = relationship("User", secondary=likes, back_populates="liked_videos")
    comments = relationship("Comment", backref="video")
    hashtags = relationship("Hashtag", secondary=video_hashtag_association, back_populates="videos")

    # Convenience properties for templates
    @property
    def media_type(self) -> str:
        return "video"

    @property
    def url(self) -> str:
        # adjust if your storage path differs
        return f"/static/uploads/{self.filename}"

    @property
    def likes(self):
        return self.liked_by

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    caption = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    # Add a timestamp for sorting by recency
    created_at = Column(DateTime, default=datetime.utcnow)

    liked_by = relationship("User", secondary=photo_likes, back_populates="liked_photos")
    comments = relationship("Comment", backref="photo")
    hashtags = relationship("Hashtag", secondary=photo_hashtag_association, back_populates="photos")

    # Convenience properties for templates
    @property
    def media_type(self) -> str:
        return "photo"

    @property
    def url(self) -> str:
        # adjust if your storage path differs
        return f"/static/uploads/{self.filename}"

    @property
    def likes(self):
        return self.liked_by

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")

    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    photo_id = Column(Integer, ForeignKey("photos.id"), nullable=True)

class Hashtag(Base):
    __tablename__ = "hashtags"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    photos = relationship("Photo", secondary=photo_hashtag_association, back_populates="hashtags")
    videos = relationship("Video", secondary=video_hashtag_association, back_populates="hashtags")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)

    recipient_id = Column(Integer, ForeignKey("users.id"))
    recipient = relationship("User", backref="notifications")

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    type = Column(String)  # "photo", "video", "comment"
    content_id = Column(Integer)
    reason = Column(String)

    reporter_id = Column(Integer, ForeignKey("users.id"))
    reporter = relationship("User")

# add User Profile Pages
# app/models.py
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)

    bio = Column(Text, default="")  # ✅ bio field
    profile_pic = Column(String, default="/static/default-profile.png")  # ✅ profile picture URL

    media = relationship("Media", back_populates="user")

    followers = relationship(
        "User",
        secondary=follows,
        primaryjoin=id == follows.c.following_id,
        secondaryjoin=id == follows.c.follower_id,
        backref="following"
    )

# Add Notification model
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer, ForeignKey("users.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    recipient = relationship("User", foreign_keys=[recipient_id], backref="notifications_received")
    sender = relationship("User", foreign_keys=[sender_id])
