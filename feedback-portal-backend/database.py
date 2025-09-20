import sqlite3
from contextlib import contextmanager
import os
from datetime import datetime, timedelta

DATABASE = 'feedback_portal.db'

def init_db():
    """Initialize the database with required tables and indexes"""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        
        # Main tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                product TEXT NOT NULL,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                type TEXT NOT NULL CHECK(type IN ('feedback', 'complaint', 'suggestion', 'praise', 'bug')),
                message TEXT NOT NULL,
                status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Review', 'Resolved')),
                priority TEXT DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
                assigned_to TEXT,
                resolution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        
        # Ticket history/audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticket_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                field_changed TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id)
            )
        ''')
        
        # Admin users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE,
                role TEXT DEFAULT 'admin' CHECK(role IN ('admin', 'manager', 'agent')),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Categories table for better organization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Ticket tags/labels for better classification
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticket_tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id)
            )
        ''')
        
        # Customer table for better customer management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                company TEXT,
                total_tickets INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_interaction TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_type ON tickets(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_email ON tickets(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_ticket_id ON ticket_history(ticket_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_ticket_id ON ticket_tags(ticket_id)')
        
        # Insert default categories
        default_categories = [
            ('Product Issues', 'Problems related to product functionality'),
            ('Service Quality', 'Issues with service delivery or quality'),
            ('Billing', 'Payment and billing related inquiries'),
            ('Feature Request', 'Suggestions for new features'),
            ('Technical Support', 'Technical assistance and troubleshooting'),
            ('General Inquiry', 'General questions and information requests')
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO categories (category_name, description) VALUES (?, ?)
        ''', default_categories)
        
        # Insert default admin user (password: admin123)
        cursor.execute('''
            INSERT OR IGNORE INTO admin_users (username, password_hash, email, role) 
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'pbkdf2:sha256:260000$salt$hash', 'admin@company.com', 'admin'))
        
        conn.commit()
        print("Database initialized successfully with all tables and indexes!")

@contextmanager
def get_db():
    """Context manager for database connections with enhanced error handling"""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def backup_database(backup_path=None):
    """Create a backup of the database"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_feedback_portal_{timestamp}.db"
    
    try:
        with sqlite3.connect(DATABASE) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        print(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def get_database_stats():
    """Get database statistics and health metrics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Table row counts
        tables = ['tickets', 'ticket_history', 'admin_users', 'categories', 'ticket_tags', 'customers']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            stats[f'{table}_count'] = cursor.fetchone()[0]
        
        # Ticket statistics
        cursor.execute('SELECT status, COUNT(*) FROM tickets GROUP BY status')
        stats['status_breakdown'] = dict(cursor.fetchall())
        
        cursor.execute('SELECT type, COUNT(*) FROM tickets GROUP BY type')
        stats['type_breakdown'] = dict(cursor.fetchall())
        
        cursor.execute('SELECT AVG(rating) FROM tickets WHERE rating IS NOT NULL')
        avg_rating = cursor.fetchone()[0]
        stats['average_rating'] = round(avg_rating, 2) if avg_rating else 0
        
        # Recent activity (last 7 days)
        cursor.execute('''
            SELECT COUNT(*) FROM tickets 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        stats['tickets_last_week'] = cursor.fetchone()[0]
        
        # Database size
        cursor.execute('PRAGMA page_count')
        page_count = cursor.fetchone()[0]
        cursor.execute('PRAGMA page_size')
        page_size = cursor.fetchone()[0]
        stats['database_size_mb'] = round((page_count * page_size) / (1024 * 1024), 2)
        
        return stats

def cleanup_old_data(days=365):
    """Clean up old resolved tickets and history (default: older than 1 year)"""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Archive old resolved tickets
        cursor.execute('''
            DELETE FROM tickets 
            WHERE status = 'Resolved' AND resolved_at < ?
        ''', (cutoff_date,))
        
        archived_tickets = cursor.rowcount
        
        # Clean up orphaned history records
        cursor.execute('''
            DELETE FROM ticket_history 
            WHERE ticket_id NOT IN (SELECT ticket_id FROM tickets)
        ''')
        
        cleaned_history = cursor.rowcount
        
        # Clean up orphaned tags
        cursor.execute('''
            DELETE FROM ticket_tags 
            WHERE ticket_id NOT IN (SELECT ticket_id FROM tickets)
        ''')
        
        cleaned_tags = cursor.rowcount
        
        conn.commit()
        
        # Vacuum database to reclaim space
        conn.execute('VACUUM')
        
        return {
            'archived_tickets': archived_tickets,
            'cleaned_history': cleaned_history,
            'cleaned_tags': cleaned_tags
        }

def optimize_database():
    """Optimize database performance"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Update table statistics
        cursor.execute('ANALYZE')
        
        # Rebuild indexes
        cursor.execute('REINDEX')
        
        # Vacuum database
        cursor.execute('VACUUM')
        
        print("Database optimization completed!")

def export_tickets_csv(filename=None, filters=None):
    """Export tickets to CSV format"""
    import csv
    from datetime import datetime
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tickets_export_{timestamp}.csv"
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT ticket_id, name, email, product, rating, type, message, 
                   status, priority, assigned_to, created_at, updated_at, resolved_at
            FROM tickets
        '''
        
        # Apply filters if provided
        where_conditions = []
        params = []
        
        if filters:
            if filters.get('status'):
                where_conditions.append('status = ?')
                params.append(filters['status'])
            
            if filters.get('type'):
                where_conditions.append('type = ?')
                params.append(filters['type'])
            
            if filters.get('date_from'):
                where_conditions.append('created_at >= ?')
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                where_conditions.append('created_at <= ?')
                params.append(filters['date_to'])
        
        if where_conditions:
            query += ' WHERE ' + ' AND '.join(where_conditions)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        tickets = cursor.fetchall()
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            if tickets:
                writer = csv.DictWriter(csvfile, fieldnames=tickets[0].keys())
                writer.writeheader()
                for ticket in tickets:
                    writer.writerow(dict(ticket))
        
        print(f"Exported {len(tickets)} tickets to {filename}")