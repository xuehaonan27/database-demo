-- 1. 用户注册
INSERT INTO Users (username, password, email) 
VALUES ('user123', 'hashed_password', 'user123@example.com');

-- 2. 用户登录验证
SELECT user_id, username, is_admin, status 
FROM Users 
WHERE username = 'user123' AND password = 'hashed_password' AND status = 'active';

-- 3. 发布新帖子
INSERT INTO Posts (user_id, content) 
VALUES (1, '这是一条树洞内容，分享我的秘密...');

-- 4. 为帖子添加标签
INSERT INTO Tags (tag_name) 
VALUES ('情感') 
ON DUPLICATE KEY UPDATE tag_id = tag_id;

INSERT INTO Post_Tags (post_id, tag_id) 
VALUES (1, (SELECT tag_id FROM Tags WHERE tag_name = '情感'));

-- 5. 查看热门帖子（按点赞数排序）
SELECT p.post_id, p.content, p.post_time, p.likes_count, p.comments_count, p.views_count 
FROM Posts p 
WHERE p.status = 'normal' 
ORDER BY p.likes_count DESC, p.post_time DESC 
LIMIT 10;

-- 6. 查看指定标签的帖子
SELECT p.post_id, p.content, p.post_time, p.likes_count, p.comments_count 
FROM Posts p 
JOIN Post_Tags pt ON p.post_id = pt.post_id 
JOIN Tags t ON pt.tag_id = t.tag_id 
WHERE t.tag_name = '情感' AND p.status = 'normal' 
ORDER BY p.post_time DESC;

-- 7. 对帖子进行点赞
INSERT INTO Likes (user_id, post_id, like_type) 
VALUES (2, 1, 'like') 
ON DUPLICATE KEY UPDATE like_type = 'like';

-- 更新帖子的点赞计数
UPDATE Posts 
SET likes_count = (
    SELECT COUNT(*) FROM Likes 
    WHERE post_id = 1 AND like_type = 'like'
) 
WHERE post_id = 1;

-- 8. 收藏帖子
INSERT INTO Favorites (user_id, post_id) 
VALUES (2, 1) 
ON DUPLICATE KEY UPDATE favorite_time = CURRENT_TIMESTAMP;

-- 9. 对帖子进行评论
INSERT INTO Comments (post_id, user_id, content) 
VALUES (1, 3, '这条树洞太有共鸣了...');

-- 更新帖子的评论计数
UPDATE Posts 
SET comments_count = (
    SELECT COUNT(*) FROM Comments 
    WHERE post_id = 1 AND status = 'normal'
) 
WHERE post_id = 1;

-- 10. 查看用户的收藏帖子
SELECT p.post_id, p.content, p.post_time, p.likes_count, p.comments_count, f.favorite_time 
FROM Favorites f 
JOIN Posts p ON f.post_id = p.post_id 
WHERE f.user_id = 2 AND p.status = 'normal' 
ORDER BY f.favorite_time DESC;

-- 11. 搜索帖子（按关键词）
SELECT post_id, content, post_time, likes_count, comments_count 
FROM Posts 
WHERE status = 'normal' AND content LIKE '%关键词%' 
ORDER BY post_time DESC;

-- 12. 举报不良内容
INSERT INTO Reports (user_id, post_id, reason) 
VALUES (2, 1, '该内容包含不适当的语言');

-- 13. 管理员处理举报
UPDATE Reports 
SET status = 'processed', handler_id = 1, handle_time = CURRENT_TIMESTAMP 
WHERE report_id = 1;

-- 14. 管理员删除帖子
UPDATE Posts 
SET status = 'deleted' 
WHERE post_id = 1;

-- 15. 统计用户活跃度（发帖数、评论数）
SELECT u.username, 
       COUNT(DISTINCT p.post_id) AS post_count, 
       COUNT(DISTINCT c.comment_id) AS comment_count 
FROM Users u 
LEFT JOIN Posts p ON u.user_id = p.user_id AND p.status = 'normal' 
LEFT JOIN Comments c ON u.user_id = c.user_id AND c.status = 'normal' 
GROUP BY u.user_id, u.username 
ORDER BY post_count + comment_count DESC;