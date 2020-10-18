"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase
from models import db, connect_db, Message, User, Likes, Follows

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


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        # drop the data
        User.query.delete()
        Message.query.delete()
        Likes.query.delete()
        Follows.query.delete()

        # set the testing client server
        self.client = app.test_client()

        self.testuser1 = User.signup(username="testuser1",
                                    email="test@test1.com",
                                    password="testuser1",
                                    image_url=None)

        self.testuser1_id = 1111
        self.testuser1.id = self.testuser1_id

        self.testuser2 = User.signup(username="testuser2",
                                    email="test@test2.com",
                                    password="testuser2",
                                    image_url=None)

        self.testuser2_id = 2222
        self.testuser2.id = self.testuser2_id

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
    # GET /messages/new

    ################################
    # Test /messages/new POST route
    ################################
    def test_add_message_as_user_in_session(self):
        """Is a logged in user able to successfully add a message as himself/herself?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser1.id

            # Now, that session setting is saved, so we can have the rest of our tests

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            # Find the new message and check its text
            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_message_invalid_user_in_session(self):
        """Is an invalid user in the session prohibited from adding a message as that (invalid) user?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = 99999999 # user does not exist

            # Now, that session setting is saved, so we can have the rest of our tests

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    def test_add_message_no_user_in_session(self):
        """Is a logged out user unable able to add a message?"""

        with self.client as c:

            resp = c.post("/messages/new", data={"text": "Here's a message!"}, follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))


    ##############################################
    # Test /messages/<int:message_id> GET route
    ##############################################

    def test_messages_show(self):
        """Can a logged in user view a specific message?"""

        msg = Message(id=7777, 
                text="This message is a test.", 
                user_id=2222)

        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id

            msg = Message.query.get(7777)

            resp = c.get(f"/messages/{msg.id}")

            self.assertEqual(resp.status_code, 200)
            self.assertIn(msg.text, str(resp.data))

    def test_message_show_invalid_msg(self):
        """Will a user who tries to view a nonexistent message be shown a 404 page?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id
            
            resp = c.get('/messages/99999999') # message does not exist

            self.assertEqual(resp.status_code, 404)

    ##############################################
    # Test /messages/<int:message_id>/delete POST route
    ##############################################
    def test_messages_destroy(self):
        """Is a logged in user able to successfully delete a message as himself/herself?"""

        msg = Message(
            id=7777,
            text="a test message",
            user_id=self.testuser1_id
        )
        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser1.id

            # Test that the message exists
            msg = Message.query.get(7777)
            self.assertIsNotNone(msg)

            # Now, that session setting is saved, so we can have the rest of our tests
            resp = c.post('/messages/7777/delete', follow_redirects=True)
            
            self.assertEqual(resp.status_code, 200)

            # After deletion, test that the message does not exist
            msg = Message.query.get(7777)
            self.assertIsNone(msg)


    def test_messages_destroy_no_user_in_session(self):
        """Is a logged out user unable to delete any message as himself/herself?"""

        msg = Message(
            id=8888,
            text="a test message",
            user_id=self.testuser1_id
        )
        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            # Now, that session setting is saved, so we can have the rest of our tests
            resp = c.post('/messages/8888/delete', follow_redirects=True)
            
            self.assertEqual(resp.status_code, 200)  
            self.assertIn("Access unauthorized", str(resp.data))

            # After attempted deletion, test that the message still exists
            msg = Message.query.get(8888)
            self.assertIsNotNone(msg)          

    def test_messages_destroy_by_unauthorized_user(self):
        """Is a user other than message author prohibited from deleting a message?"""

        # Message is owned by testuser1
        msg = Message(
            id = 7777,
            text = "This is a test message.",
            user_id = self.testuser1_id
        )
        db.session.add(msg)
        db.session.commit()

        # Testuser2 is in logged in
        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser2.id

            resp = c.post('/messages/7777/delete', follow_redirects=True)

            self.assertEqual(resp.status_code, 200)  
            self.assertIn("Access unauthorized", str(resp.data))

            # After attempted deletion, test that the message still exists
            msg = Message.query.get(7777)
            self.assertIsNotNone(msg)      

    ##############################################
    # Test /messages/<int:message_id>/like POST route
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


    def test_add_like(self):
        """Is a logged in user able to successfully like another user's message?"""

        msg = Message(
            id=7777,
            text="a test message",
            user_id=self.testuser1_id
        )

        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser2 is logged in
                sess[CURR_USER_KEY] = self.testuser2.id

            # Now, that session setting is saved, so we can have the rest of our tests
            resp = c.post('/messages/7777/like', follow_redirects=True)
            
            # verify that status_code is 200
            self.assertEqual(resp.status_code, 200)

            # get all likes for that msg
            likes = Likes.query.filter(Likes.message_id==7777).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].message_id, 7777)
            self.assertEqual(likes[0].user_id, self.testuser2_id)
    

    def test_add_like_fail_msg_owner(self):
        """Is the owner of a message prohibited from liking that message?"""

        msg = Message(
            id=7777,
            text="a test message",
            user_id=self.testuser1_id
        )

        db.session.add(msg)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser1.id

            # Now, that session setting is saved, so we can have the rest of our tests
            resp = c.post('/messages/7777/like', follow_redirects=True)
            
            self.assertEqual(resp.status_code, 403)
            self.assertIn('You don\\\'t have the permission to access the requested resource. It is either read-protected or not readable by the server.', str(resp.data))


    def test_add_like_fail_no_user_in_session(self):
        """When there is no user logged in, is an attempt to like a message prohibited?"""

        msg = Message(
            id=7777,
            text="a test message",
            user_id=self.testuser1_id
        )

        db.session.add(msg)
        db.session.commit()

        with self.client as c:

            resp = c.post("/messages/7777/like", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            likes = Likes.query.filter(Likes.message_id==7777).all()
            self.assertEqual(len(likes), 0)

    def test_add_like_toggle_to_remove(self):
        """Can a user successfully remove a like from a message?"""

        self.setup_likes()

        # Recall that in setup_likes() testuser1 liked testuser2's message with id of 5151

        with self.client as c:
            with c.session_transaction() as sess:
                # self.testuser1 is logged in
                sess[CURR_USER_KEY] = self.testuser1.id

            # get all likes for testuser1
            likes1 = Likes.query.filter(Likes.user_id==self.testuser1_id).all()

            self.assertEqual(len(likes1), 1)

            # testuser1 will unlike message 5151
            resp = c.post('/messages/5151/like', follow_redirects=True)
            
            # verify that status_code is 200
            self.assertEqual(resp.status_code, 200)

            # get all likes for testuser1
            likes1 = Likes.query.filter(Likes.user_id==self.testuser1_id).all()

            self.assertEqual(len(likes1), 0)

            # get all likes for that msg
            likes5151 = Likes.query.filter(Likes.message_id==5151).all()

            self.assertEqual(len(likes5151), 0)

    def test_add_like_no_user_in_session(self):
        self.setup_likes()

        msg = Message.query.get(5151)
        self.assertIsNotNone(msg)

        likes_before = Likes.query.filter(Likes.message_id == msg.id).count()
        self.assertEqual(likes_before, 1)

        with self.client as c:
            resp = c.post(f'/messages/{msg.id}/like', follow_redirects=True)

            likes_after = Likes.query.filter(Likes.message_id == msg.id).count()
            self.assertEqual(resp.status_code, 200)

            self.assertEqual(likes_after, 1)







    # Other possible tests of the app:
        # Does this URL path map to a route function?
        # After a POST to this route, are we redirected?
        # After this route, does the session contain expected info?