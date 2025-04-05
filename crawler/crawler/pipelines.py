# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from itemadapter import ItemAdapter
from .models import Base, SpiderSession
from .settings import DATABASE_URI

class SessionManagerPipeline:
    def __init__(self):
        self.engine = create_engine(DATABASE_URI)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def process_item(self, item, spider):
        session = self.Session()
        
        # Check if session exists
        db_session = session.query(SpiderSession).filter_by(
            user_id=item.get('user_id')).first()
        
        if db_session:
            # Update existing session
            db_session.cookies = item.get('cookies')
            db_session.access_token = item.get('access_token')
            db_session.user_code = item.get('user_code')
            db_session.expires_at = datetime.now() + timedelta(hours=1)
        else:
            # Create new session
            db_session = SpiderSession(
                user_id=item.get('user_id'),
                cookies=item.get('cookies'),
                access_token=item.get('access_token'),
                user_code=item.get('user_code'),
                expires_at=datetime.now() + timedelta(hours=1)
            )
            session.add(db_session)
        
        session.commit()
        session.close()
        return item
