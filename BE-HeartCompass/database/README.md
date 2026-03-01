- 执行`uv run database/db-migrate.sh`数据库迁移时，生成的version文件没有自动`import pgvector`，需要手动添加
- 报错`sqlalchemy.exc.ProgrammingError: (psycopg2.errors.DuplicateObject) type "attitude" already exists`，需要在verison文件`upgrade()`函数做以下更改：

    ```python
    attitude_enum = postgresql.ENUM(
        "POSITIVE",
        "NEUTRAL",
        "NEGATIVE",
        "UNKNOWN",
        name="attitude",
        create_type=False,  # 不重新create
    )
    bind = op.get_bind()
    attitude_enum.create(bind, checkfirst=True)
    ...

        sa.Column(
            "attitude",
            attitude_enum,  # 类型
            nullable=True,
            comment="话题情绪",
        ),
    ```
