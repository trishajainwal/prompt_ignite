from database import get_db
from datetime import datetime

class Ticket:
    @staticmethod
    def create(name, email, product, rating, ticket_type, message, priority='Medium'):
        """Create a new ticket and return the ticket_id"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Insert ticket
            cursor.execute('''
                INSERT INTO tickets (name, email, product, rating, type, message, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, product, rating, ticket_type, message, priority))
            
            ticket_id = cursor.lastrowid
            
            # Update or create customer record
            cursor.execute('''
                INSERT OR REPLACE INTO customers (name, email, total_tickets, last_interaction)
                VALUES (?, ?, 
                    COALESCE((SELECT total_tickets FROM customers WHERE email = ?), 0) + 1,
                    CURRENT_TIMESTAMP)
            ''', (name, email, email))
            
            # Log the creation in history
            cursor.execute('''
                INSERT INTO ticket_history (ticket_id, field_changed, new_value, changed_by)
                VALUES (?, ?, ?, ?)
            ''', (ticket_id, 'created', 'New ticket created', 'system'))
            
            conn.commit()
            return ticket_id

    @staticmethod
    def get_by_id(ticket_id):
        """Get ticket by ID with related data"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, c.company, c.phone,
                       GROUP_CONCAT(tt.tag_name) as tags
                FROM tickets t
                LEFT JOIN customers c ON t.email = c.email
                LEFT JOIN ticket_tags tt ON t.ticket_id = tt.ticket_id
                WHERE t.ticket_id = ?
                GROUP BY t.ticket_id
            ''', (ticket_id,))
            row = cursor.fetchone()
            
            if row:
                ticket = dict(row)
                ticket['tags'] = row['tags'].split(',') if row['tags'] else []
                return ticket
            return None

    @staticmethod
    def get_all(filters=None, limit=None, offset=None):
        """Get all tickets with optional filtering, pagination"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT t.*, c.company,
                       GROUP_CONCAT(tt.tag_name) as tags
                FROM tickets t
                LEFT JOIN customers c ON t.email = c.email
                LEFT JOIN ticket_tags tt ON t.ticket_id = tt.ticket_id
            '''
            
            where_conditions = []
            params = []
            
            if filters:
                if filters.get('status'):
                    where_conditions.append('t.status = ?')
                    params.append(filters['status'])
                
                if filters.get('type'):
                    where_conditions.append('t.type = ?')
                    params.append(filters['type'])
                
                if filters.get('priority'):
                    where_conditions.append('t.priority = ?')
                    params.append(filters['priority'])
                
                if filters.get('assigned_to'):
                    where_conditions.append('t.assigned_to = ?')
                    params.append(filters['assigned_to'])
                
                if filters.get('search'):
                    where_conditions.append('''
                        (t.name LIKE ? OR t.email LIKE ? OR t.message LIKE ? OR t.product LIKE ?)
                    ''')
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term] * 4)
                
                if filters.get('date_from'):
                    where_conditions.append('t.created_at >= ?')
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    where_conditions.append('t.created_at <= ?')
                    params.append(filters['date_to'])
                
                if filters.get('rating_min'):
                    where_conditions.append('t.rating >= ?')
                    params.append(filters['rating_min'])
                
                if filters.get('rating_max'):
                    where_conditions.append('t.rating <= ?')
                    params.append(filters['rating_max'])
            
            if where_conditions:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            query += ' GROUP BY t.ticket_id ORDER BY t.created_at DESC'
            
            if limit:
                query += ' LIMIT ?'
                params.append(limit)
                
                if offset:
                    query += ' OFFSET ?'
                    params.append(offset)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            tickets = []
            for row in rows:
                ticket = dict(row)
                ticket['tags'] = row['tags'].split(',') if row['tags'] else []
                tickets.append(ticket)
            
            return tickets

    @staticmethod
    def update_status(ticket_id, status, assigned_to=None, resolution_notes=None, changed_by='admin'):
        """Update ticket status with audit logging"""
        valid_statuses = ['Pending', 'In Review', 'Resolved']
        if status not in valid_statuses:
            return False
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get current ticket data
            cursor.execute('SELECT status FROM tickets WHERE ticket_id = ?', (ticket_id,))
            current = cursor.fetchone()
            if not current:
                return False
            
            old_status = current['status']
            
            # Update ticket
            update_fields = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
            params = [status]
            
            if assigned_to is not None:
                update_fields.append('assigned_to = ?')
                params.append(assigned_to)
            
            if resolution_notes:
                update_fields.append('resolution_notes = ?')
                params.append(resolution_notes)
            
            if status == 'Resolved':
                update_fields.append('resolved_at = CURRENT_TIMESTAMP')
            
            params.append(ticket_id)
            
            cursor.execute(f'''
                UPDATE tickets SET {', '.join(update_fields)}
                WHERE ticket_id = ?
            ''', params)
            
            # Log the change in history
            cursor.execute('''
                INSERT INTO ticket_history (ticket_id, field_changed, old_value, new_value, changed_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (ticket_id, 'status', old_status, status, changed_by))
            
            if assigned_to is not None:
                cursor.execute('''
                    INSERT INTO ticket_history (ticket_id, field_changed, new_value, changed_by)
                    VALUES (?, ?, ?, ?)
                ''', (ticket_id, 'assigned_to', assigned_to, changed_by))
            
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def add_tag(ticket_id, tag_name):
        """Add a tag to a ticket"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO ticket_tags (ticket_id, tag_name)
                VALUES (?, ?)
            ''', (ticket_id, tag_name.lower().strip()))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def remove_tag(ticket_id, tag_name):
        """Remove a tag from a ticket"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM ticket_tags 
                WHERE ticket_id = ? AND tag_name = ?
            ''', (ticket_id, tag_name.lower().strip()))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def get_history(ticket_id):
        """Get ticket change history"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM ticket_history 
                WHERE ticket_id = ? 
                ORDER BY changed_at DESC
            ''', (ticket_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_statistics(date_from=None, date_to=None):
        """Get comprehensive ticket statistics"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            date_filter = ""
            params = []
            
            if date_from and date_to:
                date_filter = "WHERE created_at BETWEEN ? AND ?"
                params = [date_from, date_to]
            elif date_from:
                date_filter = "WHERE created_at >= ?"
                params = [date_from]
            elif date_to:
                date_filter = "WHERE created_at <= ?"
                params = [date_to]
            
            stats = {}
            
            # Total tickets
            cursor.execute(f'SELECT COUNT(*) FROM tickets {date_filter}', params)
            stats['total_tickets'] = cursor.fetchone()[0]
            
            # Status breakdown
            cursor.execute(f'''
                SELECT status, COUNT(*) FROM tickets {date_filter}
                GROUP BY status
            ''', params)
            stats['status_breakdown'] = dict(cursor.fetchall())
            
            # Type breakdown
            cursor.execute(f'''
                SELECT type, COUNT(*) FROM tickets {date_filter}
                GROUP BY type
            ''', params)
            stats['type_breakdown'] = dict(cursor.fetchall())
            
            # Priority breakdown
            cursor.execute(f'''
                SELECT priority, COUNT(*) FROM tickets {date_filter}
                GROUP BY priority
            ''', params)
            stats['priority_breakdown'] = dict(cursor.fetchall())
            
            # Average rating
            cursor.execute(f'''
                SELECT AVG(rating) FROM tickets 
                WHERE rating IS NOT NULL {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            ''', params)
            avg_rating = cursor.fetchone()[0]
            stats['average_rating'] = round(avg_rating, 2) if avg_rating else 0
            
            # Rating distribution
            cursor.execute(f'''
                SELECT rating, COUNT(*) FROM tickets 
                WHERE rating IS NOT NULL {date_filter.replace('WHERE', 'AND') if date_filter else ''}
                GROUP BY rating ORDER BY rating
            ''', params)
            stats['rating_distribution'] = dict(cursor.fetchall())
            
            # Most active customers
            cursor.execute(f'''
                SELECT email, name, COUNT(*) as ticket_count 
                FROM tickets {date_filter}
                GROUP BY email, name 
                ORDER BY ticket_count DESC 
                LIMIT 10
            ''', params)
            stats['top_customers'] = [dict(row) for row in cursor.fetchall()]
            
            # Popular products/services
            cursor.execute(f'''
                SELECT product, COUNT(*) as count 
                FROM tickets {date_filter}
                GROUP BY product 
                ORDER BY count DESC 
                LIMIT 10
            ''', params)
            stats['popular_products'] = [dict(row) for row in cursor.fetchall()]
            
            # Daily ticket creation (last 30 days)
            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM tickets 
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            ''')
            stats['daily_tickets'] = [dict(row) for row in cursor.fetchall()]
            
            return stats

    @staticmethod
    def get_count(filters=None):
        """Get total count of tickets with optional filters"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT COUNT(*) FROM tickets'
            where_conditions = []
            params = []
            
            if filters:
                if filters.get('status'):
                    where_conditions.append('status = ?')
                    params.append(filters['status'])
                
                if filters.get('type'):
                    where_conditions.append('type = ?')
                    params.append(filters['type'])
                
                if filters.get('search'):
                    where_conditions.append('''
                        (name LIKE ? OR email LIKE ? OR message LIKE ? OR product LIKE ?)
                    ''')
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term] * 4)
            
            if where_conditions:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]