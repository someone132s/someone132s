# login_session_repository.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import logging
from crawler.models import SpiderSession

class LoginSessionRepository:
    def __init__(self, db_uri: str):
        self.engine = create_engine(db_uri)
        self.Session = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(__name__)

    def get_active_session(self, user_id: str, dept_id: Optional[str] = None) -> Optional[SpiderSession]:
        """获取用户在指定科室（或portal）未过期的会话"""
        session = self.Session()
        try:
            query = session.query(SpiderSession)\
                .filter_by(user_id=user_id)\
                .filter(SpiderSession.expires_at > datetime.now())
            if dept_id is not None:
                query = query.filter(SpiderSession.dept_id == dept_id)
            return query.first()
        except Exception as e:
            self.logger.error(f"获取会话失败: {e}")
            raise
        finally:
            session.close()

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """
        插入或更新会话记录，使用 ON CONFLICT DO UPDATE：
         - 以 (user_id, dept_id) 为唯一键
         - 冲突时更新 cookies/access_token/user_code/expires_at
        """
        # 必要字段检查
        user_id = session_data.get('user_id')
        dept_id = session_data.get('dept_id')
        cookies  = session_data.get('cookies')
        print("#######session_data",session_data)
        # 强校验：类型 + 非空
        if not (
            isinstance(user_id, str) and user_id.strip() != "" and
            isinstance(dept_id, str) and dept_id.strip() != "" and
            isinstance(cookies, dict) and cookies
        ):
            self.logger.error(f"无效字段: user_id={user_id}, dept_id={dept_id}, cookies={cookies}")
            return False


        # 统一 expires_at 为 datetime
        expires_at = session_data.get('expires_at')
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        elif not isinstance(expires_at, datetime):
            expires_at = datetime.now() + timedelta(days=30)

        stmt = insert(SpiderSession).values(
            user_id     = user_id,
            dept_id     = dept_id,
            cookies     = cookies,
            access_token= session_data.get('access_token'),
            user_code   = session_data.get('user_code'),
            expires_at  = expires_at
        )
        # 冲突时按新的值更新
        stmt = stmt.on_conflict_do_update(
            index_elements = ['user_id', 'dept_id'],
            set_ = {
                'cookies'     : stmt.excluded.cookies,
                'access_token': stmt.excluded.access_token,
                'user_code'   : stmt.excluded.user_code,
                'expires_at'  : stmt.excluded.expires_at,
            }
        )

        session = self.Session()
        try:
            session.execute(stmt)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"save_session 执行失败: {e}")
            raise
        finally:
            session.close()

    def invalidate_session(self, user_id: str, dept_id: Optional[str] = None) -> bool:
        """作废用户在指定科室（或portal）所有会话"""
        session = self.Session()
        try:
            query = session.query(SpiderSession).filter_by(user_id=user_id)
            if dept_id is not None:
                query = query.filter_by(dept_id=dept_id)
            query.delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"作废会话失败: {e}")
            raise
        finally:
            session.close()
