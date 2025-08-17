from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging
from config import DB_CONFIG
from database.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DB_CONFIG.DATABASE_URL
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database engine and session factory"""
        try:
            # Configure engine based on database type
            if self.database_url.startswith('sqlite'):
                self.engine = create_engine(
                    self.database_url,
                    echo=DB_CONFIG.ECHO_SQL,
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30
                    }
                )
            else:
                self.engine = create_engine(
                    self.database_url,
                    echo=DB_CONFIG.ECHO_SQL,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info(f"Database initialized: {self.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get database session for synchronous use"""
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def get_db_session() -> Generator[Session, None, None]:
    """Get database session - convenience function"""
    with db_manager.get_session() as session:
        yield session

def init_database():
    """Initialize database tables"""
    db_manager.create_tables()

def close_database():
    """Close database connections"""
    db_manager.close()

# Database utilities
class DatabaseUtils:
    """Utility functions for database operations"""
    
    @staticmethod
    def bulk_insert(session: Session, model_instances: list, batch_size: int = 1000):
        """Bulk insert with batching for better performance"""
        try:
            for i in range(0, len(model_instances), batch_size):
                batch = model_instances[i:i + batch_size]
                session.bulk_save_objects(batch)
                session.commit()
            logger.info(f"Bulk inserted {len(model_instances)} records")
        except Exception as e:
            session.rollback()
            logger.error(f"Bulk insert failed: {e}")
            raise
    
    @staticmethod
    def cleanup_old_records(session: Session, model_class, timestamp_field: str, 
                          days_to_keep: int = 30):
        """Clean up old records to manage database size"""
        from datetime import datetime, timedelta
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            deleted_count = session.query(model_class).filter(
                getattr(model_class, timestamp_field) < cutoff_date
            ).delete(synchronize_session=False)
            
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old records from {model_class.__tablename__}")
            return deleted_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Cleanup failed for {model_class.__tablename__}: {e}")
            raise
    
    @staticmethod
    def get_table_stats(session: Session, model_class) -> dict:
        """Get basic statistics about a table"""
        try:
            count = session.query(model_class).count()
            
            # Get the first and last records if they have timestamp
            first_record = None
            last_record = None
            
            if hasattr(model_class, 'timestamp'):
                first_record = session.query(model_class).order_by(
                    model_class.timestamp.asc()
                ).first()
                last_record = session.query(model_class).order_by(
                    model_class.timestamp.desc()
                ).first()
            
            return {
                'table_name': model_class.__tablename__,
                'total_records': count,
                'first_record_date': first_record.timestamp if first_record else None,
                'last_record_date': last_record.timestamp if last_record else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {model_class.__tablename__}: {e}")
            return {'error': str(e)}