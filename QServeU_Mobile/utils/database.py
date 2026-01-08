from supabase import create_client
import os
from dotenv import load_dotenv
import bcrypt
from datetime import date
from datetime import datetime, timedelta, timezone

load_dotenv()


class MobileDatabase:
    """Database handler for mobile app"""

    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')

        if not url or not key:
            print("⚠️ Warning: SUPABASE credentials missing in .env")
            self.client = None
            return

        try:
            self.client = create_client(url, key)
        except Exception as e:
            # Handle proxy parameter issue in newer versions
            print(f"⚠️ Supabase connection issue: {e}")
            try:
                from supabase import create_client as create_client_alt
                self.client = create_client_alt(supabase_url=url, supabase_key=key)
            except:
                self.client = None

    # ==================== AUTH ====================

    def hash_password(self, password):
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password, hashed):
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode())
        except:
            return False

    def register_student(self, student_data):
        """Register new student"""
        try:
            # Check if student ID exists
            existing = self.client.table('students').select('id').eq('student_id', student_data['student_id']).execute()
            if existing.data:
                return {'success': False, 'message': 'Student ID already exists'}

            hashed_password = self.hash_password(student_data['password'])

            new_student = {
                'student_id': student_data['student_id'],
                'full_name': student_data['full_name'],
                'email': student_data['email'],
                'password_hash': hashed_password,
                'course': student_data.get('course', ''),
                'year_level': student_data.get('year_level', '')
            }

            response = self.client.table('students').insert(new_student).execute()

            if response.data:
                return {'success': True, 'message': 'Registration successful', 'student': response.data[0]}
            return {'success': False, 'message': 'Registration failed'}

        except Exception as e:
            return {'success': False, 'message': str(e)}

    def login_student(self, identifier, password):
        """Login student using Email OR Student ID (Two-Step Fix)"""
        try:
            # STEP 1: Try to find user by Student ID
            response = self.client.table('students').select('*').eq('student_id', identifier).execute()

            # STEP 2: If not found, try to find by Email
            if not response.data:
                response = self.client.table('students').select('*').eq('email', identifier).execute()

            # If still no data, the user really doesn't exist
            if not response.data:
                return {'success': False, 'message': 'User not found'}

            student = response.data[0]

            # STEP 3: Check Password
            # A. Try Plain Text (for old accounts or if hashing failed)
            if student.get('password_hash') == password:
                return {'success': True, 'message': 'Login successful', 'student': student}

            # B. Try Hashed Password (for new secure accounts)
            if self.verify_password(password, student.get('password_hash', '')):
                return {'success': True, 'message': 'Login successful', 'student': student}
            else:
                return {'success': False, 'message': 'Incorrect password'}

        except Exception as e:
            print(f"Error logging in: {e}")
            return {'success': False, 'message': 'Login error'}

    # ==================== DATA & QUEUES ====================

    def get_offices(self):
        try:
            response = self.client.table('offices').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching offices: {e}")
            return []

    def get_active_queue_count(self, student_id):
        """
        STRICT CHECK: Only returns true if student is actually Waiting or Serving.
        Ignores 'Cancelled' so students can request again.
        """
        try:
            today = date.today().isoformat()
            response = self.client.table('queues').select('*')\
                .eq('student_id', student_id)\
                .gte('created_at', today)\
                .in_('status', ['waiting', 'serving'])\
                .execute()
            return len(response.data) if response.data else 0
        except:
            return 0

    def get_student_queue(self, student_id):
        """
        Get the student's latest queue.
        FIX: Look back 24 hours instead of just 'today' to fix timezone issues.
        """
        try:
            # CHANGE THIS LINE: Instead of date.today(), go back 1 day
            yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

            response = self.client.table('queues').select('*, offices(name)') \
                .eq('student_id', student_id) \
                .gte('created_at', yesterday) \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()

            if response.data:
                queue = response.data[0]
                if queue['status'] in ['waiting', 'serving', 'cancelled']:
                    return queue
            return None
        except Exception as e:
            print(f"Error getting queue: {e}")
            return None

    def create_queue(self, student_id, office_id, purpose):
        """Create a new queue entry with Recycling Logic & Fix for Missing Column"""
        try:
            # ====================================================
            # 1. FIX: Use strict check (Ignores Cancelled Queues)
            # ====================================================
            # 1. Check if already in queue (NOW USING YOUR NEW FUNCTION)
            if self.get_active_queue_count(student_id) > 0:  # <--- Now it is used!
                active = self.get_student_queue(student_id)
                num = active['queue_number'] if active else '???'
                return {'success': False, 'message': f"You are already in queue {num}"}

            # 2. Get Office Details
            office_resp = self.client.table('offices').select('*').eq('id', office_id).execute()
            if not office_resp.data:
                return {'success': False, 'message': "Office not found"}

            office_data = office_resp.data[0]
            prefix = office_data.get('queue_prefix', 'Q')

            # --- LOGIC START: FIND AVAILABLE NUMBER (YOUR ORIGINAL LOGIC) ---

            # A. Get ACTIVE numbers (Strictly Unavailable)
            active_q_resp = self.client.table('queues') \
                .select('queue_number') \
                .eq('office_id', office_id) \
                .in_('status', ['waiting', 'serving']) \
                .execute()

            used_numbers = set()
            for q in active_q_resp.data:
                try:
                    num = int(q['queue_number'].replace(prefix, ''))
                    used_numbers.add(num)
                except:
                    continue

            # B. Get COOLDOWN numbers (Finished < 10 mins ago)
            cooldown_numbers = set()

            if len(used_numbers) > 0:
                ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

                # Query 1: Recently Completed
                completed_resp = self.client.table('queues') \
                    .select('queue_number') \
                    .eq('office_id', office_id) \
                    .eq('status', 'completed') \
                    .gt('completed_at', ten_mins_ago) \
                    .execute()

                # Query 2: Recently Cancelled
                cancelled_resp = self.client.table('queues') \
                    .select('queue_number') \
                    .eq('office_id', office_id) \
                    .eq('status', 'cancelled') \
                    .gt('cancelled_at', ten_mins_ago) \
                    .execute()

                # Combine results
                for q in (completed_resp.data + cancelled_resp.data):
                    try:
                        num = int(q['queue_number'].replace(prefix, ''))
                        cooldown_numbers.add(num)
                    except:
                        continue

            # C. Find lowest available number
            next_num = 1
            while (next_num in used_numbers) or (next_num in cooldown_numbers):
                next_num += 1
                if next_num > 999: break

            queue_number = f"{prefix}{next_num:03d}"

            # --- LOGIC END ---

            # 4. Count Wait
            count_resp = self.client.table('queues') \
                .select('*', count='exact') \
                .eq('office_id', office_id) \
                .eq('status', 'waiting') \
                .execute()

            people_ahead = count_resp.count if count_resp.count is not None else 0

            # 5. Insert
            new_queue = {
                'student_id': student_id,
                'office_id': office_id,
                'queue_number': queue_number,
                'purpose': purpose,
                'status': 'waiting',
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            res = self.client.table('queues').insert(new_queue).execute()

            if res.data:
                result_queue = res.data[0]
                result_queue['people_ahead'] = people_ahead
                return {'success': True, 'queue': result_queue}

            return {'success': False, 'message': "Database insert failed"}

        except Exception as e:
            print(f"Create Queue Error: {e}")
            return {'success': False, 'message': str(e)}

    # ==================== FEEDBACK ====================

    def submit_feedback(self, office_id, student_id, queue_id, rating, comment):
        """Submit feedback for a completed queue"""
        try:
            feedback_data = {
                'office_id': office_id,
                'student_id': student_id,
                'queue_id': queue_id,
                'rating': rating,
                'comment': comment
            }
            response = self.client.table('feedback').insert(feedback_data).execute()
            return {'success': True, 'message': 'Feedback submitted'}
        except Exception as e:
            print(f"Feedback error: {e}")
            return {'success': False, 'message': str(e)}

    def get_pending_feedback(self, student_id):
        """Check if there is a completed queue that hasn't been rated yet"""
        try:
            # 1. Get the most recent 'completed' queue for this student
            # We also fetch the office name to show "Rate your visit to [Office]"
            queue_resp = self.client.table('queues') \
                .select('*, offices(name)') \
                .eq('student_id', student_id) \
                .eq('status', 'completed') \
                .order('created_at', desc=True) \
                .limit(1) \
                .execute()

            if not queue_resp.data:
                return None

            recent_queue = queue_resp.data[0]

            # 2. Check if this specific queue_id already exists in the 'feedback' table
            feedback_resp = self.client.table('feedback') \
                .select('id') \
                .eq('queue_id', recent_queue['id']) \
                .execute()

            # If NO feedback found, return this queue so the app knows to ask for a rating
            if not feedback_resp.data:
                return recent_queue

            return None

        except Exception as e:
            print(f"Error checking pending feedback: {e}")
            return None

    def update_student(self, student_id, full_name, year_level, password=None):
        """Update student credentials"""
        try:
            updates = {
                'full_name': full_name,
                'year_level': year_level
            }

            # Only update password if the user actually typed a new one
            if password and password.strip():
                updates['password_hash'] = self.hash_password(password)

            # Perform the update on Supabase
            response = self.client.table('students').update(updates).eq('student_id', student_id).execute()

            if response.data:
                return {'success': True, 'message': 'Update successful', 'student': response.data[0]}

            return {'success': False, 'message': 'Update failed or no changes made'}

        except Exception as e:
            print(f"Update error: {e}")
            return {'success': False, 'message': str(e)}

    def cancel_student_queue(self, queue_id, student_id):
        """Allow a student to cancel their own waiting queue"""
        try:
            # 1. Verify ownership and status first
            # We only allow cancelling if it's 'waiting' (not serving or completed)
            response = self.client.table('queues').select('*') \
                .eq('id', queue_id) \
                .eq('student_id', student_id) \
                .eq('status', 'waiting') \
                .execute()

            if not response.data:
                return {'success': False, 'message': 'Queue cannot be cancelled (might be serving already)'}

            # 2. Update status to cancelled
            update_data = {
                'status': 'cancelled',
                'cancelled_at': datetime.now(timezone.utc).isoformat(),
                'notes': 'Cancelled by student'
            }

            self.client.table('queues').update(update_data).eq('id', queue_id).execute()

            return {'success': True, 'message': 'Queue cancelled successfully'}

        except Exception as e:
            print(f"Cancel Error: {e}")
            return {'success': False, 'message': str(e)}
