我们被要求借助大模型完成数据库大作业，要求完成一个数据库设计开发的全过程案例，包括从需求分析、概念建模、创建数据库、数据库连接接口以及基本的数据库操作。

步骤一：罗列业务需求
对于树洞类型的应用（类似北大树洞，匿名发帖），核心功能如下：

用户注册与登录系统
匿名发布帖子（树洞内容）
查看所有帖子或按条件筛选帖子
对帖子进行回复（评论）
对帖子进行点赞/踩操作
收藏感兴趣的帖子
搜索帖子功能（按关键词）
热门帖子排序展示
个人中心（查看自己发布/回复/收藏的帖子）
举报不良内容
管理员审核和管理帖子内容
用户隐私保护（匿名发帖但系统后台可追溯）

步骤二：数据库设计
1. 表结构设计
根据上述业务需求，我们需要设计以下表结构：
1. 用户表 (Users)

user_id：用户ID（主键）
username：用户名
password：密码（加密存储）
email：电子邮箱
registration_time：注册时间
last_login_time：最后登录时间
is_admin：是否为管理员（布尔值）
status：账号状态（正常/禁用）

2. 帖子表 (Posts)

post_id：帖子ID（主键）
user_id：发帖用户ID（外键）
content：帖子内容
post_time：发帖时间
update_time：更新时间
likes_count：点赞数量
dislikes_count：踩数量
comments_count：评论数量
views_count：浏览次数
status：帖子状态（正常/被删除/被举报）

3. 评论表 (Comments)

comment_id：评论ID（主键）
post_id：所属帖子ID（外键）
user_id：评论用户ID（外键）
content：评论内容
comment_time：评论时间
parent_comment_id：父评论ID（用于嵌套回复，可为空）
likes_count：点赞数量
status：评论状态（正常/被删除/被举报）

4. 点赞表 (Likes)

like_id：点赞ID（主键）
user_id：用户ID（外键）
post_id：帖子ID（外键，可为空）
comment_id：评论ID（外键，可为空）
like_type：点赞类型（喜欢/不喜欢）
like_time：点赞时间

5. 收藏表 (Favorites)

favorite_id：收藏ID（主键）
user_id：用户ID（外键）
post_id：帖子ID（外键）
favorite_time：收藏时间

6. 举报表 (Reports)

report_id：举报ID（主键）
user_id：举报用户ID（外键）
post_id：被举报帖子ID（外键，可为空）
comment_id：被举报评论ID（外键，可为空）
reason：举报原因
report_time：举报时间
status：处理状态（未处理/已处理/忽略）
handler_id：处理人ID（外键，可为空）
handle_time：处理时间（可为空）

7. 标签表 (Tags)

tag_id：标签ID（主键）
tag_name：标签名称
create_time：创建时间

8. 帖子标签关联表 (Post_Tags)

id：关联ID（主键）
post_id：帖子ID（外键）
tag_id：标签ID（外键）

以下给出flask后端代码和数据库操作代码，请生成前端HTML代码。
并且介绍如何跑起来这个前后端服务。