from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, timedelta
import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from pymysql.cursors import DictCursor

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(days=7)

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'TreeHole',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def login_required(f):
    """检查用户是否登录的装饰器"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    """检查用户是否为管理员的装饰器"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('需要管理员权限', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 首页 - 显示所有帖子
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    tag = request.args.get('tag')
    search = request.args.get('search')
    sort_by = request.args.get('sort', 'newest')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 构建查询
            sql_base = """
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
                sql_base += " AND EXISTS (SELECT 1 FROM Post_Tags pt2 JOIN Tags t2 ON pt2.tag_id = t2.tag_id WHERE pt2.post_id = p.post_id AND t2.tag_name = %s)"
                params.append(tag)
            
            # 添加搜索条件
            if search:
                sql_base += " AND p.content LIKE %s"
                params.append(f"%{search}%")
            
            sql_base += " GROUP BY p.post_id"
            
            # 排序
            if sort_by == 'hot':
                sql_base += " ORDER BY p.likes_count DESC, p.comments_count DESC, p.post_time DESC"
            elif sort_by == 'controversial':
                sql_base += " ORDER BY (p.comments_count / (p.views_count + 1)) DESC, p.post_time DESC"
            else:  # 默认按最新排序
                sql_base += " ORDER BY p.post_time DESC"
            
            # 计算总数
            count_sql = "SELECT COUNT(DISTINCT p.post_id) AS total FROM (" + sql_base + ") AS p"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 分页
            sql = sql_base + " LIMIT %s OFFSET %s"
            offset = (page - 1) * per_page
            params.extend([per_page, offset])
            
            cursor.execute(sql, params)
            posts = cursor.fetchall()
            
            # 获取热门标签
            cursor.execute("""
            SELECT t.tag_name, COUNT(pt.post_id) as post_count
            FROM Tags t
            JOIN Post_Tags pt ON t.tag_id = pt.tag_id
            JOIN Posts p ON pt.post_id = p.post_id
            WHERE p.status = 'normal'
            GROUP BY t.tag_id
            ORDER BY post_count DESC
            LIMIT 10
            """)
            popular_tags = cursor.fetchall()
            
    finally:
        conn.close()
    
    # 格式化日期
    for post in posts:
        post['post_time'] = post['post_time'].strftime('%Y-%m-%d %H:%M')
        if post['tags']:
            post['tag_list'] = post['tags'].split(',')
        else:
            post['tag_list'] = []
    
    return render_template('index.html', 
                          posts=posts, 
                          page=page,
                          pages=(total + per_page - 1) // per_page,
                          total=total,
                          search=search,
                          tag=tag,
                          sort_by=sort_by,
                          popular_tags=popular_tags)

# 用户注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        
        # 简单验证
        if not username or not password or not email:
            flash('请填写所有必填字段', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 检查用户名是否已存在
                cursor.execute("SELECT username FROM Users WHERE username = %s", (username))
                if cursor.fetchone():
                    flash('用户名已存在', 'danger')
                    return render_template('register.html')
                
                # 检查邮箱是否已注册
                cursor.execute("SELECT email FROM Users WHERE email = %s", (email))
                if cursor.fetchone():
                    flash('邮箱已被注册', 'danger')
                    return render_template('register.html')
                
                # 创建新用户
                cursor.execute(
                    "INSERT INTO Users (username, password, email) VALUES (%s, %s, %s)",
                    (username, hashed_password, email)
                )
                conn.commit()
                
                flash('注册成功，请登录', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f'注册失败: {str(e)}', 'danger')
            return render_template('register.html')
        finally:
            conn.close()
            
    return render_template('register.html')

# 用户登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT user_id, username, password, is_admin, status FROM Users WHERE username = %s",
                    (username)
                )
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    if user['status'] != 'active':
                        flash('账号已被禁用', 'danger')
                        return render_template('login.html')
                    
                    # 设置会话
                    session.permanent = True
                    session['user_id'] = user['user_id']
                    session['username'] = user['username']
                    session['is_admin'] = bool(user['is_admin'])
                    
                    # 更新最后登录时间
                    cursor.execute(
                        "UPDATE Users SET last_login_time = NOW() WHERE user_id = %s",
                        (user['user_id'])
                    )
                    conn.commit()
                    
                    next_page = request.args.get('next', url_for('index'))
                    flash('登录成功', 'success')
                    return redirect(next_page)
                else:
                    flash('用户名或密码错误', 'danger')
        finally:
            conn.close()
    
    return render_template('login.html')

# 用户注销
@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

# 发布新帖子
@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        content = request.form['content']
        tags = request.form.getlist('tags')
        
        if not content:
            flash('请输入帖子内容', 'danger')
            return render_template('new_post.html')
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 创建帖子
                cursor.execute(
                    "INSERT INTO Posts (user_id, content) VALUES (%s, %s)",
                    (session['user_id'], content)
                )
                post_id = cursor.lastrowid
                
                # 处理标签
                if tags:
                    for tag in tags:
                        tag = tag.strip()
                        if tag:
                            # 确保标签存在
                            cursor.execute(
                                "INSERT INTO Tags (tag_name) VALUES (%s) ON DUPLICATE KEY UPDATE tag_id = LAST_INSERT_ID(tag_id)",
                                (tag)
                            )
                            tag_id = cursor.lastrowid
                            
                            # 关联帖子和标签
                            cursor.execute(
                                "INSERT INTO Post_Tags (post_id, tag_id) VALUES (%s, %s)",
                                (post_id, tag_id)
                            )
                
                conn.commit()
                flash('帖子发布成功', 'success')
                return redirect(url_for('view_post', post_id=post_id))
        except Exception as e:
            conn.rollback()
            flash(f'发布失败: {str(e)}', 'danger')
        finally:
            conn.close()
    
    # 获取热门标签
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
            SELECT t.tag_name, COUNT(pt.post_id) as post_count
            FROM Tags t
            JOIN Post_Tags pt ON t.tag_id = pt.tag_id
            GROUP BY t.tag_id
            ORDER BY post_count DESC
            LIMIT 20
            """)
            popular_tags = cursor.fetchall()
    finally:
        conn.close()
    
    return render_template('new_post.html', popular_tags=popular_tags)

# 查看帖子详情
@app.route('/post/<int:post_id>')
def view_post(post_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 获取帖子详情
            cursor.execute("""
            SELECT p.post_id, p.content, p.post_time, p.likes_count, p.dislikes_count, 
                   p.comments_count, p.views_count, GROUP_CONCAT(t.tag_name) AS tags
            FROM Posts p
            LEFT JOIN Post_Tags pt ON p.post_id = pt.post_id
            LEFT JOIN Tags t ON pt.tag_id = t.tag_id
            WHERE p.post_id = %s AND p.status = 'normal'
            GROUP BY p.post_id
            """, (post_id))
            
            post = cursor.fetchone()
            if not post:
                flash('帖子不存在或已被删除', 'danger')
                return redirect(url_for('index'))
            
            # 格式化日期并处理标签
            post['post_time'] = post['post_time'].strftime('%Y-%m-%d %H:%M')
            if post['tags']:
                post['tag_list'] = post['tags'].split(',')
            else:
                post['tag_list'] = []
            
            # 获取评论
            cursor.execute("""
            SELECT c.comment_id, c.content, c.comment_time, c.user_id, c.likes_count,
                   c.parent_comment_id, u.username
            FROM Comments c
            JOIN Users u ON c.user_id = u.user_id
            WHERE c.post_id = %s AND c.status = 'normal'
            ORDER BY c.comment_time
            """, (post_id))
            
            comments = cursor.fetchall()
            for comment in comments:
                comment['comment_time'] = comment['comment_time'].strftime('%Y-%m-%d %H:%M')
            
            # 检查当前用户是否点赞/收藏
            user_liked = False
            user_favorited = False
            
            if 'user_id' in session:
                cursor.execute(
                    "SELECT like_type FROM Likes WHERE user_id = %s AND post_id = %s",
                    (session['user_id'], post_id)
                )
                like = cursor.fetchone()
                if like:
                    user_liked = like['like_type'] == 'like'
                
                cursor.execute(
                    "SELECT favorite_id FROM Favorites WHERE user_id = %s AND post_id = %s",
                    (session['user_id'], post_id)
                )
                user_favorited = cursor.fetchone() is not None
            
            # 更新浏览次数
            cursor.execute(
                "UPDATE Posts SET views_count = views_count + 1 WHERE post_id = %s",
                (post_id)
            )
            conn.commit()
            
    finally:
        conn.close()
    
    return render_template(
        'view_post.html',
        post=post,
        comments=comments,
        user_liked=user_liked,
        user_favorited=user_favorited
    )

# 点赞帖子
@app.route('/post/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    like_type = request.form.get('like_type', 'like')
    if like_type not in ['like', 'dislike']:
        return jsonify({'success': False, 'message': '无效的操作'})
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查帖子是否存在
            cursor.execute(
                "SELECT post_id FROM Posts WHERE post_id = %s AND status = 'normal'",
                (post_id)
            )
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': '帖子不存在或已被删除'})
            
            # 检查是否已经点赞/踩过
            cursor.execute(
                "SELECT like_id, like_type FROM Likes WHERE user_id = %s AND post_id = %s",
                (session['user_id'], post_id)
            )
            existing_like = cursor.fetchone()
            
            if existing_like:
                if existing_like['like_type'] == like_type:
                    # 取消点赞/踩
                    cursor.execute(
                        "DELETE FROM Likes WHERE like_id = %s",
                        (existing_like['like_id'])
                    )
                    message = "已取消" + ("点赞" if like_type == 'like' else "踩")
                else:
                    # 改变点赞/踩类型
                    cursor.execute(
                        "UPDATE Likes SET like_type = %s, like_time = NOW() WHERE like_id = %s",
                        (like_type, existing_like['like_id'])
                    )
                    message = "已改为" + ("点赞" if like_type == 'like' else "踩")
            else:
                # 新增点赞/踩
                cursor.execute(
                    "INSERT INTO Likes (user_id, post_id, like_type) VALUES (%s, %s, %s)",
                    (session['user_id'], post_id, like_type)
                )
                message = "已" + ("点赞" if like_type == 'like' else "踩")
            
            # 更新帖子的点赞/踩计数
            cursor.execute("""
            UPDATE Posts p
            SET p.likes_count = (SELECT COUNT(*) FROM Likes WHERE post_id = p.post_id AND like_type = 'like'),
                p.dislikes_count = (SELECT COUNT(*) FROM Likes WHERE post_id = p.post_id AND like_type = 'dislike')
            WHERE p.post_id = %s
            """, (post_id))
            
            # 获取最新的点赞/踩数
            cursor.execute(
                "SELECT likes_count, dislikes_count FROM Posts WHERE post_id = %s",
                (post_id)
            )
            counts = cursor.fetchone()
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': message,
                'likes_count': counts['likes_count'],
                'dislikes_count': counts['dislikes_count']
            })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    finally:
        conn.close()

# 收藏帖子
@app.route('/post/<int:post_id>/favorite', methods=['POST'])
@login_required
def favorite_post(post_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查帖子是否存在
            cursor.execute(
                "SELECT post_id FROM Posts WHERE post_id = %s AND status = 'normal'",
                (post_id)
            )
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': '帖子不存在或已被删除'})
            
            # 检查是否已经收藏
            cursor.execute(
                "SELECT favorite_id FROM Favorites WHERE user_id = %s AND post_id = %s",
                (session['user_id'], post_id)
            )
            existing_favorite = cursor.fetchone()
            
            if existing_favorite:
                # 取消收藏
                cursor.execute(
                    "DELETE FROM Favorites WHERE favorite_id = %s",
                    (existing_favorite['favorite_id'])
                )
                message = "已取消收藏"
                is_favorited = False
            else:
                # 添加收藏
                cursor.execute(
                    "INSERT INTO Favorites (user_id, post_id) VALUES (%s, %s)",
                    (session['user_id'], post_id)
                )
                message = "已收藏"
                is_favorited = True
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': message,
                'is_favorited': is_favorited
            })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
    finally:
        conn.close()

# 添加评论
@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    parent_comment_id = request.form.get('parent_comment_id')
    
    if not content:
        flash('评论内容不能为空', 'danger')
        return redirect(url_for('view_post', post_id=post_id))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 检查帖子是否存在
            cursor.execute(
                "SELECT post_id FROM Posts WHERE post_id = %s AND status = 'normal'",
                (post_id)
            )
            if not cursor.fetchone():
                flash('帖子不存在或已被删除', 'danger')
                return redirect(url_for('index'))
            
            # 检查父评论
            if parent_comment_id:
                cursor.execute(
                    "SELECT comment_id FROM Comments WHERE comment_id = %s AND post_id = %s AND status = 'normal'",
                    (parent_comment_id, post_id)
                )
                if not cursor.fetchone():
                    flash('回复的评论不存在或已被删除', 'danger')
                    return redirect(url_for('view_post', post_id=post_id))
            
            # 添加评论
            cursor.execute(
                "INSERT INTO Comments (post_id, user_id, content, parent_comment_id) VALUES (%s, %s, %s, %s)",
                (post_id, session['user_id'], content, parent_comment_id if parent_comment_id else None)
            )
            
            # 更新帖子的评论计数
            cursor.execute(
                "UPDATE Posts SET comments_count = (SELECT COUNT(*) FROM Comments WHERE post_id = %s AND status = 'normal') WHERE post_id = %s",
                (post_id, post_id)
            )
            
            conn.commit()
            flash('评论发布成功', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'评论失败: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('view_post', post_id=post_id))

# 用户中心 - 我的帖子
@app.route('/user/posts')
@login_required
def user_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 查询用户的帖子
            cursor.execute("""
            SELECT p.post_id, p.content, p.post_time, p.likes_count, p.comments_count, 
                   p.views_count, GROUP_CONCAT(t.tag_name) AS tags
            FROM Posts p
            LEFT JOIN Post_Tags pt ON p.post_id = pt.post_id
            LEFT JOIN Tags t ON pt.tag_id = t.tag_id
            WHERE p.user_id = %s AND p.status = 'normal'
            GROUP BY p.post_id
            ORDER BY p.post_time DESC
            LIMIT %s OFFSET %s
            """, (session['user_id'], per_page, (page - 1) * per_page))
            
            posts = cursor.fetchall()
            
            # 获取总数
            cursor.execute(
                "SELECT COUNT(*) AS total FROM Posts WHERE user_id = %s AND status = 'normal'",
                (session['user_id'])
            )
            total = cursor.fetchone()['total']
    finally:
        conn.close()
    
    # 格式化日期
    for post in posts:
        post['post_time'] = post['post_time'].strftime('%Y-%m-%d %H:%M')
        if post['tags']:
            post['tag_list'] = post['tags'].split(',')
        else:
            post['tag_list'] = []
    
    return render_template(
        'user_posts.html',
        posts=posts,
        page=page,
        pages=(total + per_page - 1) // per_page,
        total=total
    )

# 用户中心 - 我的收藏
@app.route('/user/favorites')
@login_required
def user_favorites():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 查询用户的收藏
            cursor.execute("""
            SELECT p.post_id, p.content, p.post_time, p.likes_count, p.comments_count, 
                   p.views_count, GROUP_CONCAT(t.tag_name) AS tags, f.favorite_time
            FROM Favorites f
            JOIN Posts p ON f.post_id = p.post_id
            LEFT JOIN Post_Tags pt ON p.post_id = pt.post_id
            LEFT JOIN Tags t ON pt.tag_id = t.tag_id
            WHERE f.user_id = %s AND p.status = 'normal'
            GROUP BY p.post_id
            ORDER BY f.favorite_time DESC
            LIMIT %s OFFSET %s
            """, (session['user_id'], per_page, (page - 1) * per_page))
            
            posts = cursor.fetchall()
            
            # 获取总数
            cursor.execute(
                """
                SELECT COUNT(*) AS total 
                FROM Favorites f 
                JOIN Posts p ON f.post_id = p.post_id 
                WHERE f.user_id = %s AND p.status = 'normal'
                """,
                (session['user_id'])
            )
            total = cursor.fetchone()['total']
    finally:
        conn.close()
    
    # 格式化日期
    for post in posts:
        post['post_time'] = post['post_time'].strftime('%Y-%m-%d %H:%M')
        post['favorite_time'] = post['favorite_time'].strftime('%Y-%m-%d %H:%M')
        if post['tags']:
            post['tag_list'] = post['tags'].split(',')
        else:
            post['tag_list'] = []
    
    return render_template(
        'user_favorites.html',
        posts=posts,
        page=page,
        pages=(total + per_page - 1) // per_page,
        total=total
    )

# 管理员页面 - 帖子管理
@app.route('/admin/posts')
@login_required
@admin_required
def admin_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    status = request.args.get('status', 'all')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 构建查询
            sql_base = """
            SELECT p.post_id, p.content, p.post_time, p.likes_count, p.dislikes_count, 
                  p.comments_count, p.views_count, p.status, u.username
            FROM Posts p
            JOIN Users u ON p.user_id = u.user_id
            """
            params = []
            
            # 添加状态筛选
            if status != 'all':
                sql_base += " WHERE p.status = %s"
                params.append(status)
            
            sql_base += " ORDER BY p.post_time DESC"
            
            # 计算总数
            count_sql = "SELECT COUNT(*) AS total FROM (" + sql_base + ") AS p"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 分页
            sql = sql_base + " LIMIT %s OFFSET %s"
            offset = (page - 1) * per_page
            params.extend([per_page, offset])
            
            cursor.execute(sql, params)
            posts = cursor.fetchall()
    finally:
        conn.close()
    
    # 格式化日期
    for post in posts:
        post['post_time'] = post['post_time'].strftime('%Y-%m-%d %H:%M')
    
    return render_template(
        'admin_posts.html',
        posts=posts,
        page=page,
        pages=(total + per_page - 1) // per_page,
        total=total,
        status=status
    )

# 管理员操作 - 修改帖子状态
@app.route('/admin/post/<int:post_id>/status', methods=['POST'])
@login_required
@admin_required
def update_post_status(post_id):
    new_status = request.form.get('status')
    if new_status not in ['normal', 'deleted', 'hidden']:
        flash('无效的状态值', 'danger')
        return redirect(url_for('admin_posts'))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE Posts SET status = %s WHERE post_id = %s",
                (new_status, post_id)
            )
            conn.commit()
            flash('帖子状态已更新', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'操作失败: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('admin_posts'))

if __name__ == '__main__':
    app.run(debug=True)