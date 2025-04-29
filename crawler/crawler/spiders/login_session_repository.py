# login_session_repository.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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
        """插入或更新会话记录，支持 portal 和 ccd（dept_id）"""
        session = self.Session()
        try:
            # 统一 expires_at 为 datetime
            expires_at = session_data.get('expires_at')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.now() + timedelta(days=30)

            # 必须包含 dept_id
            dept_id = session_data.get('dept_id')
            if dept_id is None:
                raise ValueError("保存会话时必须包含 'dept_id' 字段")

            existing = session.query(SpiderSession)\
                .filter(SpiderSession.user_id == session_data['user_id'],
                        SpiderSession.dept_id == dept_id)\
                .first()
            if existing:
                existing.cookies = session_data['cookies']
                existing.access_token = session_data.get('access_token', existing.access_token)
                existing.user_code = session_data.get('user_code', existing.user_code)
                existing.expires_at = expires_at
            else:
                new_s = SpiderSession(
                    user_id=session_data['user_id'],
                    cookies=session_data['cookies'],
                    access_token=session_data.get('access_token'),
                    user_code=session_data.get('user_code'),
                    expires_at=expires_at,
                    dept_id=dept_id
                )
                session.add(new_s)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存会话失败: {e}")
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
