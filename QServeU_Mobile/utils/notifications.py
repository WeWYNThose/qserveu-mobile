from plyer import notification


class NotificationManager:
    def __init__(self):
        self.last_people_ahead = -1
        self.last_status = None
        self.last_note = ""

    def send_notification(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name='QServeU',
                timeout=10,
            )
        except Exception as e:
            print(f"Notification Error: {e}")

    def update_status(self, queue_data):
        if not queue_data:
            return

        current_status = queue_data.get('status')
        people_ahead = queue_data.get('people_ahead', 0)
        queue_number = queue_data.get('queue_number')
        current_note = queue_data.get('notes', '') or ""

        # 1. HANDLE SKIPPED (Check if 'Skipped' is in the notes)
        if 'Skipped' in current_note and self.last_note != current_note:
            self.send_notification(
                "⚠️ You were Skipped",
                f"Queue {queue_number}: You were not around, so you were moved to the back."
            )
            self.last_note = current_note
            # We return here so we don't trigger the "people ahead" notification at the same time
            return

        # 2. HANDLE CANCELLED
        if current_status == 'cancelled' and self.last_status != 'cancelled':
            reason = current_note if current_note else "Cancelled by staff"
            self.send_notification(
                "❌ Queue Cancelled",
                f"Queue {queue_number} was cancelled. Reason: {reason}"
            )
            self.last_status = current_status
            return

        # 3. HANDLE YOUR TURN
        if current_status == 'serving' and self.last_status != 'serving':
            self.send_notification(
                "🔊 IT'S YOUR TURN!",
                f"Queue {queue_number} - Please proceed to the counter immediately!"
            )
            self.last_status = current_status
            return

        # 4. HANDLE PANEL / POSITION UPDATES
        if current_status == 'waiting':
            # Only notify if the number of people ahead CHANGED (and it's not a skip)
            if people_ahead != self.last_people_ahead and self.last_status == 'waiting':
                self.send_notification(
                    "QServeU Status",
                    f"Queue: {queue_number} | {people_ahead} people ahead of you."
                )

            # Special alert if you are next
            if people_ahead == 1 and self.last_people_ahead != 1:
                self.send_notification(
                    "⚠️ You are Next!",
                    "Get ready! There is only 1 person ahead of you."
                )

        # Save state for next check
        self.last_status = current_status
        self.last_people_ahead = people_ahead
        self.last_note = current_note   