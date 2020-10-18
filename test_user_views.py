"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

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

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        # drop the data
        User.query.delete()
        Message.query.delete()
        Likes.query.delete()
        Follows.query.delete()

        # set the testing client server
        self.client = app.test_client()

        self.testuser1 = User.signup(
            username="testuser1",
            email="test1@test1.com",
            password="testuser1",
            image_url=None
        )

        self.testuser1_id = 1111
        self.testuser1.id = self.testuser1_id

        self.testuser2 = User.signup(
            username="testuser2",
            email="test2@test2.com",
            password="testuser2",
            image_url=None
        )

        self.testuser2_id = 2222
        self.testuser2.id = self.testuser2_id

        self.testuser3 = User.signup(
            username="carlos",
            email="carlos@carlos.com",
            password="carlos",
            image_url=None
        )

        self.testuser3_id = 3333
        self.testuser3.id = self.testuser3_id

        self.testuser4 = User.signup(
            username="daniel",
            email="daniel@daniel.com",
            password="daniel",
            image_url=None
        )

        self.testuser4_id = 4444
        self.testuser4.id = self.testuser4_id

        db.session.commit()


    def tearDown(self):
        """Remove sample data."""
        resp = super().tearDown()
        db.session.rollback()
        return resp


    ######
    #
    # Test routes and view functions (with & w/o auth)
    #
    ######
    # Each view should return a valid response. This means:
        # The response code is what you expect and
        # Light HTML testing shows that the response is what you expect.

    # ROUTES TO TEST
    # GET /, logged in
    # GET /, logged out

    ##############################################
    # Test /users GET route
    ##############################################

    def test_list_users(self):
        """Is a user able to successfully view the users page?"""

        with self.client as c:
            resp = c.get('/users')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f'<p>@{self.testuser1.username}</p>', str(resp.data))

    def test_list_users_search(self):
        """Can a user successfully include a search term to filter the users viewed on the users page?"""

        with self.client as c:
            resp = c.get('/users?q=test')

            self.assertIn("@testuser1", str(resp.data))
            self.assertIn("@testuser2", str(resp.data))
            self.assertNotIn("@carlos", str(resp.data))
            self.assertNotIn("@daniel", str(resp.data))


    ##############################################
    # Test /users/<int:user_id> GET route
    ##############################################

    def test_users_show(self):
        """Can a user successfully view the detail page for another user?"""

        with self.client as c:
            resp = c.get(f'/users/{self.testuser2_id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn("@testuser2", str(resp.data))

        # Could also test that the messages display in chronological order with most recent messages on top

        # Could also test that at most 100 messages are displayed

    ##############################################
    # Test /users/<int:user_id>/likes GET route
    ##############################################
    
    def setup_likes(self):
        """Do setup work to be used in tests of showing nad removing users' likes"""

        m1 = Message(text="trending warble", user_id=self.testuser1_id)
        m2 = Message(text="Eating some lunch", user_id=self.testuser1_id)
        m3 = Message(id=5151, text="likable warble", user_id=self.testuser2_id)
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        # Testuser1 likes message 5151 by testuser2
        like = Likes(user_id=self.testuser1_id,
            message_id=5151)

        db.session.add(like)
        db.session.commit()

    def test_users_show_with_likes(self):
        self.setup_likes()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser1_id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser1", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')

            # in the HTML response, find all li tags with class="stat"; these will be the Messages, Following, Followers, and Likes stats for the user.
            # found returns a list
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)

            # Test for a count of 2 messages
            self.assertIn("2", found[0].text)

            # Test for a count of 0 followers
            self.assertIn("0", found[1].text)

            # Test for a count of 0 following
            self.assertIn("0", found[2].text)

            # Test for a count of 1 like
            self.assertIn("1", found[3].text)

    ##############################################
    # Test /users/<int:user_id>/following GET route
    ##############################################
    def test_show_following_user_in_session(self):
        """Can a logged in user successfully see the following page for another user?"""

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser1.id

            # Now, that session setting is saved, so we can have the rest of our tests
            resp = c.get('/users/2222/following')
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@testuser2", str(resp.data))
            self.assertIn('<a href="/users/2222/following">0</a>', str(resp.data))

    def test_show_following_no_user_in_session(self):
        """Is a logged out user unable to see the following page for another user?"""

        with self.client as c:
            resp=c.get('/users/2222/following', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    ##############################################
    # Test /users/<int:user_id>/followers GET route
    ##############################################
    def test_users_followers_other_user(self):
        """Can a logged in user successfully see the follower page for another user?"""

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser1.id

            # Now, that session setting is saved, so we can have the rest of our tests
            resp = c.get('/users/2222/followers')
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@testuser2", str(resp.data))
            self.assertIn('<a href="/users/2222/following">0</a>', str(resp.data))


    def test_users_followers_no_user_in_session(self):
        """Is a logged out user unable to see the follower page for another user?"""
        with self.client as c:
            resp = c.get('/users/2222/followers', follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    # POST /users/follow/<int:follow_id>
    # POST /users/stop-following/<int:follow_id>
    # GET /users/profile
    # POST /users/profile
    # POST /users/delete
    # GET /login
    # POST /login
    # GET /logout
    # GET /signup
    # POST /signup
