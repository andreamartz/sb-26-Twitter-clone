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
    #
    # Test User model
    #
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

        # User should have no messages & no followers & follow no one & have no likes
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
        self.assertEqual(len(u.following), 0)
        self.assertEqual(len(u.likes), 0)


    def test_user_repr(self):
        """Does the repr method work as expected?"""

        self.assertEqual(
            repr(self.user2), "<User #2222: jackson, jackson@jackson.com>")

    ################################
    #
    # Test following
    #
    ################################
    def test_user_following(self):
        """Does the following relationship accurately show when user1 is following user2?"""

        self.user1.following.append(self.user2)
        db.session.commit()

        # test if user2 is in the list of users that user1 is following
        self.assertIn(self.user2, self.user1.following)
        self.assertNotIn(self.user1, self.user2.following)
        self.assertEqual(len(self.user1.following), 1)
        self.assertEqual(len(self.user1.followers), 0)
        self.assertEqual(len(self.user2.following), 0)
        self.assertEqual(len(self.user2.followers), 1)


    def test_is_following(self):
        """Does is_following successfully detect when user1 is following user2?"""

        self.user1.following.append(self.user2)
        db.session.commit()

        self.assertTrue(self.user1.is_following(self.user2))
        self.assertFalse(self.user2.is_following(self.user1))

    def test_is_following_false(self):
        """Does is_following successfully detect when user1 is not following user2?"""

        self.assertFalse(self.user1.is_following(self.user2))
        self.assertFalse(self.user2.is_following(self.user1))

    def test_is_followed_by(self):
        """Does is_followed_by successfully detect when user1 is followed by user2?"""

        self.user1.followers.append(self.user2)
        db.session.commit()

        self.assertTrue(self.user1.is_followed_by(self.user2))
        self.assertFalse(self.user2.is_followed_by(self.user1))


    def test_is_followed_by_false(self):
        """Does is_followed_by successfully detect when user1 is not followed by user2?"""

        self.assertFalse(self.user1.is_followed_by(self.user2))
        self.assertFalse(self.user2.is_followed_by(self.user1))

    ################################
    #
    # Test user creation
    #
    ################################
    def test_create_user(self):
        """Does User.signup successfully create a new user given valid credentials?"""

        user3_test = User.signup("username3", "email3@email3.com", "password3", None)
        db.session.commit()

        self.assertTrue(user3_test)
        self.assertEqual(user3_test.username, "username3")
        self.assertEqual(user3_test.email, "email3@email3.com")
        self.assertNotEqual(user3_test.password, "password3")

        #Bcrypt strings start with '$2b$'
        self.assertTrue(user3_test.password.startswith("$2b$"))

    def test_create_user_fail_missing_username(self):
        """Does User.signup fail to create a new user when username is missing?"""
        invalid_user = User.signup(None, "email@email.com", "password", None)

        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()
            
        # self.assertFalse(invalid_user)


    def test_create_user_fail_email_missing(self):
        """Does User.signup fail to create a new user when email address is missing?"""

        invalid_user = User.signup("username", None, "password", None)
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()


    def test_create_user_fail_email_invalid(self):
        """Does User.signup fail to create a new user when email address given has invalid format?"""

        invalid_user = User.signup("username", "emailemail.com", "password", None)
        with self.assertRaises(exc.IntegrityError) as context:
            db.session.commit()

    def test_create_user_fail_password_missing(self):
        """Does User.signup fail to create a new user when password is missing?"""

        with self.assertRaises(ValueError) as context:
            invalid_user = User.signup("username", "email@email.com", None, None)
            db.session.commit()

    def test_create_user_fail_password_too_short(self):
        """Does User.signup fail to create a new user when password is too short?"""

        with self.assertRaises(exc.IntegrityError) as context:
            invalid_user = User.signup("username", "email@email.com", "abc", None)
            
            db.session.commit()
