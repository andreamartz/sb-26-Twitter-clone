"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data
db.create_all()

# Disable CSRF usage from WTForms, since it's a pain to test
app.config['WTF_CSRF_ENABLED'] = False

app.config['TESTING'] = True
app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']


class UserModelTestCase(TestCase):
    """Test model for users."""

    # runs before each test
    def setUp(self):
        """Add sample data."""

        # Drop all database tables and re-create them
        db.drop_all()
        db.create_all()

        # Create two new users
        user1 = User.signup("allison", "allison@allison.com",
                            "allison", "http://lorempixel.com/400/400/people/1")
        user1.id = 1111

        user2 = User.signup("jackson", "jackson@jackson.com", "jackson", None)
        user2.id = 2222

        # Add the new users to the database
        db.session.commit()

        # Attach the users to this test case
        self.user1 = user1
        self.user2 = user2

        # set the testing client server
        self.client = app.test_client()

    # runs after each test
    def tearDown(self):
        """Remove sample data."""

        db.session.rollback()

    ################################
    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)