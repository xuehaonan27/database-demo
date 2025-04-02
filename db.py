import pymysql
from pymysql.cursors import DictCursor
import hashlib
from datetime import datetime

class TreeHoleDB:
    """树洞应用数据库操作类"""
    
    def __init__(self, host='localhost', user='root', password='password', database='TreeHole'):
        """初始化数据库连接"""
        self.conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=DictCursor
        )
    
    def __del__(self):
        """关闭数据库连接"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def _hash_password(self, password):
        """简单的密码哈希函数"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    # 增: 用户注册
    def create_user(self, username, password, email):
        """创建新用户"""
        try:
            with self.conn.cursor() as cursor:
                hashed_password = self._hash_password(password)
                sql = """
                INSERT INTO Users (username, password, email)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (username, hashed_password, email))
            self.conn.commit()
            return True, "用户创建成功"
        except pymysql.err.IntegrityError as e:
            # 处理唯一约束违反的情况
            if "Duplicate entry" in str(e):
                if "username" in str(e):
                    return False, "用户名已存在"
                elif "email" in str(e):
                    return False, "邮箱已被注册"
            return False, f"创建用户失败: {str(e)}"
        except Exception as e:
            self.conn.rollback()
            return False, f"创建用户失败: {str(e)}"
    
    # 查: 用户登录验证
    def verify_user(self, username, password):
        """验证用户名和密码"""
        try:
            with self.conn.cursor() as cursor:
                hashed_password = self._hash_password(password)
                sql = """
                SELECT user_id, username, is_admin, status
                FROM Users
                WHERE username = %s AND password = %s
                """
                cursor.execute(sql, (username, hashed_password))
                user = cursor.fetchone()
                
                if user:
                    if user['status'] == 'active':
                        # 更新最后登录时间
                        update_sql = "UPDATE Users SET last_login_time = NOW() WHERE user_id = %s"
                        cursor.execute(update_sql, (user['user_id']))
                        self.conn.commit()
                        return True, user
                    else:
                        return False, "账号已被禁用"
                else:
                    return False, "用户名或密码错误"
        except Exception as e:
            return False, f"登录验证失败: {str(e)}"
    
    # 增: 发布新帖子
    def create_post(self, user_id, content, tags=None):
        """发布新帖子，可选添加标签"""
        try:
            with self.conn.cursor() as cursor:
                # 创建帖子
                sql = "INSERT INTO Posts (user_id, content) VALUES (%s, %s)"
                cursor.execute(sql, (user_id, content))
                post_id = cursor.lastrowid
                
                # 添加标签（如果提供）
                if tags and isinstance(tags, list) and len(tags) > 0:
                    for tag_name in tags:
                        # 先确保标签存在
                        tag_sql = """
                        INSERT INTO Tags (tag_name) 
                        VALUES (%s) 
                        ON DUPLICATE KEY UPDATE tag_id = LAST_INSERT_ID(tag_id)
                        """
                        cursor.execute(tag_sql, (tag_name))
                        tag_id = cursor.lastrowid if cursor.lastrowid else cursor.execute("SELECT tag_id FROM Tags WHERE tag_name = %s", (tag_name)).fetchone()['tag_id']
                        
                        # 关联帖子和标签
                        link_sql = "INSERT INTO Post_Tags (post_id, tag_id) VALUES (%s, %s)"
                        cursor.execute(link_sql, (post_id, tag_id))
                
            self.conn.commit()
            return True, {"post_id": post_id, "message": "帖子发布成功"}
        except Exception as e:
            self.conn.rollback()
            return False, f"发布帖子失败: {str(e)}"
    
    # 删: 删除帖子
    def delete_post(self, post_id, user_id, is_admin=False):
        """删除帖子（用户只能删除自己的帖子，管理员可删除任何帖子）"""
        try:
            with self.conn.cursor() as cursor:
                # 检查帖子是否存在以及权限
                check_sql = "SELECT user_id FROM Posts WHERE post_id = %s"
                cursor.execute(check_sql, (post_id))
                post = cursor.fetchone()
                
                if not post:
                    return False, "帖子不存在"
                
                if not is_admin and post['user_id'] != user_id:
                    return False, "没有权限删除此帖子"
                
                # 软删除帖子
                sql = "UPDATE Posts SET status = 'deleted' WHERE post_id = %s"
                cursor.execute(sql, (post_id))
            
            self.conn.commit()
            return True, "帖子已成功删除"
        except Exception as e:
            self.conn.rollback()
            return False, f"删除帖子失败: {str(e)}"
    
    # 改: 点赞/踩帖子
    def like_post(self, user_id, post_id, like_type='like'):
        """点赞或踩帖子"""
        try:
            with self.conn.cursor() as cursor:
                # 检查帖子是否存在
                check_sql = "SELECT post_id FROM Posts WHERE post_id = %s AND status = 'normal'"
                cursor.execute(check_sql, (post_id))
                if not cursor.fetchone():
                    return False, "帖子不存在或已被删除"
                
                # 检查是否已经点赞/踩过
                like_check_sql = "SELECT like_id, like_type FROM Likes WHERE user_id = %s AND post_id = %s"
                cursor.execute(like_check_sql, (user_id, post_id))
                existing_like = cursor.fetchone()
                
                if existing_like:
                    if existing_like['like_type'] == like_type:
                        # 取消点赞/踩
                        delete_sql = "DELETE FROM Likes WHERE like_id = %s"
                        cursor.execute(delete_sql, (existing_like['like_id']))
                        message = "已取消" + ("点赞" if like_type == 'like' else "踩")
                    else:
                        # 改变点赞/踩类型
                        update_sql = "UPDATE Likes SET like_type = %s, like_time = NOW() WHERE like_id = %s"
                        cursor.execute(update_sql, (like_type, existing_like['like_id']))
                        message = "已改为" + ("点赞" if like_type == 'like' else "踩")
                else:
                    # 新增点赞/踩
                    insert_sql = "INSERT INTO Likes (user_id, post_id, like_type) VALUES (%s, %s, %s)"
                    cursor.execute(insert_sql, (user_id, post_id, like_type))
                    message = "已" + ("点赞" if like_type == 'like' else "踩")
                
                # 更新帖子的点赞/踩计数
                update_counts_sql = """
                UPDATE Posts p
                SET p.likes_count = (SELECT COUNT(*) FROM Likes WHERE post_id = p.post_id AND like_type = 'like'),
                    p.dislikes_count = (SELECT COUNT(*) FROM Likes WHERE post_id = p.post_id AND like_type = 'dislike')
                WHERE p.post_id = %s
                """
                cursor.execute(update_counts_sql, (post_id))
            
            self.conn.commit()
            return True, message
        except Exception as e:
            self.conn.rollback()
            return False, f"操作失败: {str(e)}"
    
    # 查: 获取帖子列表
    def get_posts(self, page=1, per_page=10, tag=None, search=None, sort_by='newest'):
        """获取帖子列表，支持分页、标签筛选、搜索和排序"""
        try:
            with self.conn.cursor() as cursor:
                # 基础SQL
                sql = """
                SELECT p.post_id, p.content, p.post_time, p.likes_count, p.dislikes_count, 
                       p.comments_count, p.views_count, GROUP_CONCAT(t.tag_name) AS tags
                FROM Posts p
                LEFT JOIN Post_Tags pt ON p.post_id = pt.post_id
                LEFT JOIN Tags t ON pt.tag_id = t.tag_id
                WHERE p.status = 'normal'
                """
                params = []
                
                # 添加标签筛选
                if tag:
                    sql += " AND EXISTS (SELECT 1 FROM Post_Tags pt2 JOIN Tags t2 ON pt2.tag_id = t2.tag_id WHERE pt2.post_id = p.post_id AND t2.tag_name = %s)"
                    params.append(tag)
                
                # 添加搜索条件
                if search:
                    sql += " AND p.content LIKE %s"
                    params.append(f"%{search}%")
                
                # 添加分组
                sql += " GROUP BY p.post_id"
                
                # 排序
                if sort_by == 'hot':
                    sql += " ORDER BY p.likes_count DESC, p.comments_count DESC, p.post_time DESC"
                elif sort_by == 'controversial':
                    sql += " ORDER BY (p.comments_count / (p.views_count + 1)) DESC, p.post_time DESC"
                else:  # 默认按最新排序
                    sql += " ORDER BY p.post_time DESC"
                
                # 分页
                sql += " LIMIT %s OFFSET %s"
                offset = (page - 1) * per_page
                params.extend([per_page, offset])
                
                # 执行查询
                cursor.execute(sql, params)
                posts = cursor.fetchall()
                
                # 获取总数（用于分页）
                count_sql = """
                SELECT COUNT(DISTINCT p.post_id) AS total
                FROM Posts p
                """
                if tag:
                    count_sql += """
                    JOIN Post_Tags pt ON p.post_id = pt.post_id
                    JOIN Tags t ON pt.tag_id = t.tag_id
                    WHERE p.status = 'normal' AND t.tag_name = %s
                    """
                    if search:
                        count_sql += " AND p.content LIKE %s"
                        cursor.execute(count_sql, (tag, f"%{search}%"))
                    else:
                        cursor.execute(count_sql, (tag))
                else:
                    count_sql += " WHERE p.status = 'normal'"
                    if search:
                        count_sql += " AND p.content LIKE %s"
                        cursor.execute(count_sql, (f"%{search}%"))
                    else:
                        cursor.execute(count_sql)
                
                total = cursor.fetchone()['total']
                
            return True, {
                "posts": posts,
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page
            }
        except Exception as e:
            return False, f"获取帖子列表失败: {str(e)}"