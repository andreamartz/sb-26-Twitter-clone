"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py

import os
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    # runs before each test
    def setUp(self):
        """Create test client, add sample data."""
        
        db.drop_all()
        db.create_all()

        user1 = User.signup("allison", "allison@allison.com",
                            "allison", "http://lorempixel.com/400/400/people/1")
        user1.id = 1111

        user2 = User.signup("jackson", "jackson@jackson.com", "jackson", None)
        user2.id = 2222

        db.session.commit()

        self.user1 = user1
        self.user2 = user2

        # set the testing client server
        self.client = app.test_client()

    # runs after each test
    def tearDown(self):
        """Remove sample data."""

        db.session.rollback()

    def test_message_model(self):
        """Does basic model work?"""

        m = Message(text="This message is only a test.",
            user_id=self.user1.id)

        db.session.add(m)
        db.session.commit()

        # Message should exist
        self.assertTrue(m)

        # User should have one message
        self.assertEqual(len(self.user1.messages), 1)

        # The message should say, "This message is only a test."
        self.assertEqual(self.user1.messages[0].text, "This message is only a test.")

    def test_message_likes(self):
        """Does add_like successfully allow a user to like another user's message?"""

        m = Message(text="This message is only a test.",
            user_id=self.user1.id)

        db.session.add(m)
        db.session.commit()

        m = Message.query.get_or_404(1)
        self.user2.likes.append(m)

        self.assertEqual(len(self.user2.likes), 1)
        self.assertEqual(self.user2.likes[0], m)
