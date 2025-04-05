from .init_db import db_initializer

if __name__ == "__main__":
    print("强制重建数据库表...")
    db_initializer.init_db(force=True)
    print("数据库表重建完成")
