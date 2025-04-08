from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from crawler.models import SpiderSession

class SessionRepository:
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
            existing = session.query(SpiderSession)\
                .filter_by(user_id=session_data['user_id'])\
                .first()
                
            if existing:
                existing.cookies = session_data['cookies']
                existing.access_token = session_data['access_token']
                existing.user_code = session_data['user_code']
                existing.expires_at = session_data['expires_at']
            else:
                new_session = SpiderSession(**session_data)
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
