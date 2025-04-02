-- 创建数据库
CREATE DATABASE IF NOT EXISTS TreeHole;
USE TreeHole;

-- 用户表
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    registration_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_time DATETIME,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled', 'banned'))
);

-- 帖子表
CREATE TABLE Posts (
    post_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    post_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    likes_count INT NOT NULL DEFAULT 0,
    dislikes_count INT NOT NULL DEFAULT 0,
    comments_count INT NOT NULL DEFAULT 0,
    views_count INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (status IN ('normal', 'deleted', 'reported', 'hidden')),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- 评论表
CREATE TABLE Comments (
    comment_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    comment_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parent_comment_id INT DEFAULT NULL,
    likes_count INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (status IN ('normal', 'deleted', 'reported')),
    FOREIGN KEY (post_id) REFERENCES Posts(post_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (parent_comment_id) REFERENCES Comments(comment_id)
);

-- 点赞表
CREATE TABLE Likes (
    like_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    post_id INT DEFAULT NULL,
    comment_id INT DEFAULT NULL,
    like_type VARCHAR(10) NOT NULL CHECK (like_type IN ('like', 'dislike')),
    like_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (post_id) REFERENCES Posts(post_id),
    FOREIGN KEY (comment_id) REFERENCES Comments(comment_id),
    CONSTRAINT check_target CHECK (
        (post_id IS NOT NULL AND comment_id IS NULL) OR 
        (post_id IS NULL AND comment_id IS NOT NULL)
    ),
    CONSTRAINT unique_user_post_like UNIQUE (user_id, post_id),
    CONSTRAINT unique_user_comment_like UNIQUE (user_id, comment_id)
);

-- 收藏表
CREATE TABLE Favorites (
    favorite_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    post_id INT NOT NULL,
    favorite_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (post_id) REFERENCES Posts(post_id),
    CONSTRAINT unique_user_post_favorite UNIQUE (user_id, post_id)
);

-- 举报表
CREATE TABLE Reports (
    report_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    post_id INT DEFAULT NULL,
    comment_id INT DEFAULT NULL,
    reason TEXT NOT NULL,
    report_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'ignored')),
    handler_id INT DEFAULT NULL,
    handle_time DATETIME DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (post_id) REFERENCES Posts(post_id),
    FOREIGN KEY (comment_id) REFERENCES Comments(comment_id),
    FOREIGN KEY (handler_id) REFERENCES Users(user_id),
    CONSTRAINT check_report_target CHECK (
        (post_id IS NOT NULL AND comment_id IS NULL) OR 
        (post_id IS NULL AND comment_id IS NOT NULL)
    )
);

-- 标签表
CREATE TABLE Tags (
    tag_id INT AUTO_INCREMENT PRIMARY KEY,
    tag_name VARCHAR(50) NOT NULL UNIQUE,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 帖子标签关联表
CREATE TABLE Post_Tags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    tag_id INT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES Posts(post_id),
    FOREIGN KEY (tag_id) REFERENCES Tags(tag_id),
    CONSTRAINT unique_post_tag UNIQUE (post_id, tag_id)
);

-- 创建索引以提高查询性能
CREATE INDEX idx_posts_user_id ON Posts(user_id);
CREATE INDEX idx_posts_post_time ON Posts(post_time);
CREATE INDEX idx_comments_post_id ON Comments(post_id);
CREATE INDEX idx_comments_user_id ON Comments(user_id);
CREATE INDEX idx_likes_user_id ON Likes(user_id);
CREATE INDEX idx_likes_post_id ON Likes(post_id);
CREATE INDEX idx_likes_comment_id ON Likes(comment_id);
CREATE INDEX idx_favorites_user_id ON Favorites(user_id);
CREATE INDEX idx_favorites_post_id ON Favorites(post_id);
CREATE INDEX idx_post_tags_post_id ON Post_Tags(post_id);
CREATE INDEX idx_post_tags_tag_id ON Post_Tags(tag_id);