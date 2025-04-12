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

    def get_active_session(self, user_id: str) -> Optional[SpiderSession]:
        """获取用户有效会话"""
        session = self.Session()
        try:
            return session.query(SpiderSession)\
                .filter_by(user_id=user_id)\
                .filter(SpiderSession.expires_at > datetime.now())\
                .first()
        except Exception as e:
            self.logger.error(f"获取会话失败: {str(e)}")
            raise
        finally:
            session.close()

    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """保存或更新会话"""
        session = self.Session()
        try:
            # 确保expires_at是datetime对象
            expires_at = session_data.get('expires_at')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.now() + timedelta(days=30)
                
            existing = session.query(SpiderSession)\
                .filter_by(user_id=session_data['user_id'])\
                .first()
                
            if existing:
                existing.cookies = session_data['cookies']
                existing.access_token = session_data.get('access_token', existing.access_token)
                existing.user_code = session_data.get('user_code', existing.user_code)
                existing.expires_at = expires_at
            else:
                new_session = SpiderSession(
                    user_id=session_data['user_id'],
                    cookies=session_data['cookies'],
                    access_token=session_data.get('access_token'),
                    user_code=session_data.get('user_code'),
                    expires_at=expires_at
                )
                session.add(new_session)
                
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"保存会话失败: {str(e)}")
            raise
        finally:
            session.close()

    def invalidate_session(self, user_id: str) -> bool:
        """作废用户会话"""
        session = self.Session()
        try:
            session.query(SpiderSession)\
                .filter_by(user_id=user_id)\
                .delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            self.logger.error(f"作废会话失败: {str(e)}")
            raise
        finally:
            session.close()
